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

from database.db import db_manager
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
                self.processed_md5s.discard(md5_hex)
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

    def add_document(self, kb_id: str, doc_id: str, file_path: str):
        """
        添加单个文档到向量库

        Args:
            kb_id: 知识库ID
            doc_id: 文档ID
            file_path: 文件绝对路径
        """
        try:
            # 0. 更新状态为 running
            db_manager.update_document_status(kb_id, doc_id, "running")

            # 1. 加载文件
            documents: List[Document] = load_file(file_path)
            if not documents:
                logger.warning(f"文件为空 or 加载失败: {file_path}")
                db_manager.update_document_status(
                    kb_id, doc_id, "failed", "文件加载失败或内容为空"
                )
                return

            # 2. 注入 Metadata
            for doc in documents:
                doc.metadata["kb_id"] = kb_id
                doc.metadata["doc_id"] = doc_id
                doc.metadata["source"] = file_path

            # 3. 分块
            split_docs: List[Document] = self.splitter.split_documents(documents)
            if not split_docs:
                logger.warning(f"分块结果为空: {file_path}")
                db_manager.update_document_status(
                    kb_id, doc_id, "failed", "文档分块结果为空"
                )
                return

            # 4. 存入 Chroma
            self.vector_store.add_documents(split_docs)

            # 5. 更新状态为 completed
            db_manager.update_document_status(kb_id, doc_id, "completed")
            logger.info(
                f"文档已向量化: kb_id={kb_id}, doc_id={doc_id}, path={file_path}"
            )

        except Exception as e:
            logger.exception(f"向量化失败: {file_path}, error: {e}")
            db_manager.update_document_status(kb_id, doc_id, "failed", str(e))

    def delete_document(self, kb_id: str, doc_id: str):
        """删除指定文档的向量"""
        try:
            # Chroma 的 delete 方法通常支持 where 过滤
            # 确保 collection 存在
            self.vector_store._collection.delete(
                where={"$and": [{"kb_id": kb_id}, {"doc_id": doc_id}]}
            )
            logger.info(f"文档向量已删除: kb_id={kb_id}, doc_id={doc_id}")
        except Exception as e:
            logger.error(f"删除文档向量失败: {e}")

    def delete_knowledge_base(self, kb_id: str):
        """删除整个知识库的向量"""
        try:
            self.vector_store._collection.delete(where={"kb_id": kb_id})
            logger.info(f"知识库向量已删除: kb_id={kb_id}")
        except Exception as e:
            logger.error(f"删除知识库向量失败: {e}")

    def get_retriever(self, k: Optional[int] = None, **kwargs) -> VectorStoreRetriever:
        """
        获取检索器。

        Args:
            k (Optional[int]): 检索返回的文档数量。如果未提供，使用配置中的默认值。
            **kwargs: 传递给 as_retriever 的其他参数。

        Returns:
            VectorStoreRetriever: LangChain 检索器实例。
        """
        logger.info(f"创建检索器，参数: k={k}, kwargs={kwargs}")
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
            executor.map(self.process_file, allowed_files)

    def process_file(self, file_path: str):
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
            logger.exception(f"处理文件出错 {file_path}: {e}")


# if __name__ == "__main__":
#     vector_store = VectoreStoreService()
#     # Chroma filter syntax: {"field": {"$in": [values]}}
#     filter_rule = {"kb_id": {'$in': ['775786d0-0960-4604-947a-def544c25d83']}}

#     retriever = vector_store.get_retriever(k=3, filter=filter_rule)

#     result = retriever.invoke("缠绕")

#     print(result)
