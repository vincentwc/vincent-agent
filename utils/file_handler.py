"""
文件处理工具类
"""

import hashlib
import os
from typing import List, Optional, Tuple

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document

from utils.logger_handler import get_logger

# 日志记录器
logger = get_logger(__name__)


def get_file_md5_hex(file_path: str) -> Optional[str]:
    """
    计算文件的 MD5 校验和（16 进制表示）。

    Args:
        file_path (str): 文件路径。

    Returns:
        Optional[str]: 文件的 MD5 校验和（16进制表示），如果计算失败则返回 None。
    """
    if not os.path.exists(file_path):
        logger.error(f"[get_file_md5_hex]: 文件 {file_path} 不存在")
        return None
    if not os.path.isfile(file_path):
        logger.error(f"[get_file_md5_hex]: 文件 {file_path} 不是文件")
        return None

    # 确保文件路径是绝对路径
    file_path = os.path.abspath(file_path)

    md5_hash = hashlib.md5()
    chunk_size = 4096  # 4Kb分片，避免文件过大爆内存
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except Exception as e:
        logger.error(
            f"[get_file_md5_hex]: 计算文件 {file_path} 的 MD5 时出错: {str(e)}"
        )
        return None


def listdir_with_allowed_type(
    dir_path: str, allowed_types: Tuple[str]
) -> Tuple[str]:
    """
    列出目录下所有指定类型的文件。

    Args:
        dir_path (str): 目录路径。
        allowed_types (Tuple[str]): 允许的文件类型元组，例如 (".txt", ".md")。

    Returns:
        Tuple[str]: 目录下所有指定类型的文件元组。
    """
    if not os.path.exists(dir_path):
        logger.error(f"[listdir_with_allowed_type]: 目录 {dir_path} 不存在")
        return ()
    if not os.path.isdir(dir_path):
        logger.error(f"[listdir_with_allowed_type]: {dir_path} 不是目录")
        return ()

    files = []
    try:
        for f in os.listdir(dir_path):
            if f.endswith(allowed_types):
                # 确保文件路径是绝对路径
                files.append(os.path.join(dir_path, f))
        return tuple(files)
    except Exception as e:
        logger.error(
            f"[listdir_with_allowed_type]: 遍历目录 {dir_path} 时出错: {str(e)}"
        )
        return ()


class FileLoaderFactory:
    """文件加载器工厂类"""

    @staticmethod
    def get_loader(file_path: str, **kwargs) -> Optional[BaseLoader]:
        """
        根据文件扩展名获取相应的加载器。

        Args:
            file_path (str): 文件路径。
            **kwargs: 传递给加载器的额外参数。

        Returns:
            Optional[BaseLoader]: 对应的文件加载器实例，如果不支持该类型则返回 None。
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return PyPDFLoader(file_path, password=kwargs.get("passwd"))
        elif ext == ".txt":
            return TextLoader(file_path, encoding=kwargs.get("encoding", "utf-8"))
        elif ext == ".md":
            return TextLoader(file_path, encoding=kwargs.get("encoding", "utf-8"))
        # 可以在这里扩展更多类型，如 .csv 等
        else:
            logger.warning(f"不支持的文件类型: {ext}")
            return None


def load_file(file_path: str, **kwargs) -> List[Document]:
    """
    通用文件加载函数。

    Args:
        file_path (str): 文件路径。
        **kwargs: 传递给加载器的额外参数。 例如，对于 PDF 加载器，可能需要传递密码 `passwd`；对于文本加载器，可能需要传递编码 `encoding`。

    Returns:
        List[Document]: 加载的文档列表，如果加载失败则返回空列表。
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return []

    loader = FileLoaderFactory.get_loader(file_path, **kwargs)
    if not loader:
        return []

    try:
        return loader.load()
    except Exception as e:
        logger.error(f"加载文件 {file_path} 时出错: {str(e)}")
        return []
