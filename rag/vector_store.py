"""
向量存储类
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Set

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter

from model.factory import embedding_model_factory
from utils.config_handler import config
from utils.file_handler import get_file_md5_hex, listdir_with_allowed_type, load_file
from utils.logger_handler import get_logger
from utils.path_tool import get_abs_path

logger = get_logger(__name__)


class MD5Manager:
    """
    MD5 文件状态管理器，用于记录已处理文件的 MD5 值，避免重复处理。
    线程安全。
    """

    def __init__(self, md5_store_path: str):
        """
        初始化 MD5 管理器。

        Args:
            md5_store_path (str): MD5 记录文件路径。
        """
        self.md5_store_path = get_abs_path(md5_store_path)
        self._lock = threading.Lock()  # 确保文件写入线程安全
        self._ensure_store_exists()
        self.processed_md5s: Set[str] = self._load_md5s()

    def _ensure_store_exists(self):
        """确保 MD5 记录文件存在。"""
        if not os.path.exists(self.md5_store_path):
            os.makedirs(os.path.dirname(self.md5_store_path), exist_ok=True)
            with open(self.md5_store_path, "w", encoding="utf-8") as f:
                pass

    def _load_md5s(self) -> Set[str]:
        """加载已处理的 MD5 集合。"""
        try:
            with open(self.md5_store_path, "r", encoding="utf-8") as f:
                return {line.strip() for line in f if line.strip()}
        except Exception as e:
            logger.error(f"加载 MD5 记录文件失败: {e}")
            return set()

    def is_processed(self, md5_hex: str) -> bool:
        """检查 MD5 是否已处理。"""
        with self._lock:
            return md5_hex in self.processed_md5s

    def mark_processed(self, md5_hex: str):
        """标记 MD5 为已处理并保存。"""
        with self._lock:
            if md5_hex in self.processed_md5s:
                return

            self.processed_md5s.add(md5_hex)
            try:
                with open(self.md5_store_path, "a", encoding="utf-8") as f:
                    f.write(md5_hex + "\n")
            except Exception as e:
                logger.error(f"保存 MD5 值失败: {e}")


class VectoreStoreService:
    """
    向量存储服务类，负责文档的向量化存储与检索。
    单例模式。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(VectoreStoreService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化向量存储服务"""
        if getattr(self, "_initialized", False):
            return

        self.vector_store = Chroma(
            collection_name=config.chroma.get(
                "collection_name", "vincent_agent_collection"
            ),
            embedding_function=embedding_model_factory.get_model(),
            persist_directory=config.chroma.get("persist_directory", "./chroma_db"),
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chroma.get("chunk_size", 1000),
            chunk_overlap=config.chroma.get("chunk_overlap", 100),
            separators=config.chroma.get("separators", ["\n\n", "\n", " ", ""]),
            length_function=len,
        )

        self.md5_manager = MD5Manager(
            config.chroma.get("md5_hex_store", "md5_store.txt")
        )
        self._initialized = True

    def get_retriever(self, k: Optional[int] = None, **kwargs) -> VectorStoreRetriever:
        """
        获取检索器。

        Args:
            k (Optional[int]): 检索返回的文档数量。如果未提供，使用配置中的默认值。
            **kwargs: 传递给 as_retriever 的其他参数。

        Returns:
            VectorStoreRetriever: LangChain 检索器实例。
        """
        search_kwargs = {"k": k or config.chroma.get("k", 5)}  # 默认返回5个文档
        search_kwargs.update(kwargs)  # 合并其他参数

        return self.vector_store.as_retriever(search_kwargs=search_kwargs)

    def load_documents(self, max_workers: int = 4):
        """
        加载文档到向量存储，支持增量更新和并发处理。

        Args:
            max_workers (int): 并发处理的最大线程数，默认为 4。
        """
        data_path = get_abs_path(config.chroma.get("data_path", ""))
        logger.info(f"开始处理目录下的文档: {data_path}")

        # 获取目录下所有的文件类型的文件路径
        allowed_files = listdir_with_allowed_type(
            data_path,
            tuple(config.chroma.get("allowed_file_type", [])),
        )

        # 使用线程池并发处理文件
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(self._process_single_file, allowed_files)

    def _process_single_file(self, file_path: str):
        """
        处理单个文件：计算MD5 -> 检查重复 -> 加载 -> 分块 -> 存储。
        """
        try:
            # 1. 获取文件的md5值
            md5_hex = get_file_md5_hex(file_path)
            if not md5_hex:
                logger.error(f"计算文件 MD5 失败，跳过: {file_path}")
                return

            # 2. 检查文件是否已处理
            if self.md5_manager.is_processed(md5_hex):
                logger.info(f"文件已处理（MD5 匹配），跳过: {file_path}")
                return

            # 3. 加载文件内容
            documents: List[Document] = load_file(file_path)
            if not documents:
                logger.warning(f"文件为空或加载失败，跳过: {file_path}")
                return

            # 4. 对文档进行分块
            split_docs: List[Document] = self.splitter.split_documents(documents)
            if not split_docs:
                logger.warning(f"文件分块结果为空，跳过: {file_path}")
                return

            # 5. 存入向量数据库
            # 注意：Chroma 的 add_documents 可能涉及网络 IO (Embedding API)，并发调用可加速
            self.vector_store.add_documents(split_docs)

            # 6. 标记为已处理
            self.md5_manager.mark_processed(md5_hex)
            logger.info(f"成功处理并索引文件: {file_path}")

        except Exception as e:
            logger.error(f"处理文件出错 {file_path}: {e}")


if __name__ == "__main__":
    vector_store_service = VectoreStoreService()
    vector_store_service.load_documents()
