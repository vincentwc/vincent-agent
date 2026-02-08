import os
import shutil
import uuid
from typing import List, Optional

from fastapi import UploadFile

from rag.db import db_manager
from rag.models import KnowledgeBase, KnowledgeDocument
from utils.logger_handler import get_logger
from utils.path_tool import get_abs_path

logger = get_logger(__name__)


class KnowledgeBaseService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KnowledgeBaseService, cls).__new__(cls)
        return cls._instance

    def create_knowledge_base(
        self, name: str, tenant_id: str, description: str = None, meta_info: dict = None
    ) -> KnowledgeBase:
        """
        创建知识库业务逻辑
        """
        # 生成唯一的 collection_name，避免用户命名冲突
        collection_name = f"kb_{uuid.uuid4().hex}"

        try:
            kb = db_manager.create_knowledge_base(
                name=name,
                tenant_id=tenant_id,
                collection_name=collection_name,
                description=description,
                meta_info=meta_info,
            )
            # TODO: 在此处调用 Chroma 初始化 Collection
            logger.info(f"Created knowledge base: {name} (ID: {kb.id})")
            return kb
        except Exception as e:
            logger.error(f"Error creating knowledge base: {e}")
            raise

    def list_knowledge_bases(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> List[KnowledgeBase]:
        """
        获取知识库列表
        """
        return db_manager.list_knowledge_bases(
            tenant_id=tenant_id, limit=limit, offset=offset
        )

    def get_knowledge_base(self, kb_id: str, tenant_id: str) -> Optional[KnowledgeBase]:
        """
        获取单个知识库详情
        """
        return db_manager.get_knowledge_base(kb_id=kb_id, tenant_id=tenant_id)

    def update_knowledge_base(
        self, kb_id: str, tenant_id: str, **kwargs
    ) -> Optional[KnowledgeBase]:
        """
        更新知识库
        """
        try:
            kb = db_manager.update_knowledge_base(
                kb_id=kb_id, tenant_id=tenant_id, **kwargs
            )
            if kb:
                logger.info(f"Updated knowledge base: {kb.name} (ID: {kb.id})")
            return kb
        except Exception as e:
            logger.error(f"Error updating knowledge base: {e}")
            raise

    def delete_knowledge_base(self, kb_id: str, tenant_id: str) -> bool:
        """
        删除知识库
        """
        try:
            # 1. 获取知识库信息 (为了后续删除 collection)
            kb = self.get_knowledge_base(kb_id, tenant_id)
            if not kb:
                return False

            # 2. 从数据库删除
            success = db_manager.delete_knowledge_base(kb_id=kb_id, tenant_id=tenant_id)

            if success:
                # TODO: 在此处调用 Chroma 删除对应的 Collection
                # collection_name = kb.collection_name
                logger.info(f"Deleted knowledge base: {kb.name} (ID: {kb_id})")

            return success
        except Exception as e:
            logger.error(f"Error deleting knowledge base: {e}")
            raise

    # --- Document Management ---

    def upload_document(self, kb_id: str, file: UploadFile) -> KnowledgeDocument:
        """
        上传文档到知识库
        """
        try:
            # 1. 确定存储路径
            # 结构: data/uploads/{kb_id}/{filename}
            upload_dir = get_abs_path(f"data/uploads/{kb_id}")
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, file.filename)

            # 2. 保存文件
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # 3. 获取文件信息
            size = os.path.getsize(file_path)
            extension = os.path.splitext(file.filename)[1].lower()
            mime_type = file.content_type

            # 4. 写入数据库
            doc = db_manager.create_document(
                kb_id=kb_id,
                filename=file.filename,
                stored_path=file_path,
                size=size,
                extension=extension,
                mime_type=mime_type,
            )

            logger.info(f"Uploaded document: {file.filename} to KB: {kb_id}")
            return doc
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            raise

    def list_documents(self, kb_id: str) -> List[KnowledgeDocument]:
        """
        获取知识库下的文档列表
        """
        return db_manager.list_documents(kb_id=kb_id)

    def delete_document(self, kb_id: str, doc_id: str) -> bool:
        """
        删除文档
        """
        try:
            # 1. 获取文档信息
            doc = db_manager.get_document(kb_id=kb_id, doc_id=doc_id)
            if not doc:
                return False

            # 2. 删除本地文件
            if os.path.exists(doc.stored_path):
                try:
                    os.remove(doc.stored_path)
                except OSError as e:
                    logger.warning(f"Failed to delete file {doc.stored_path}: {e}")

            # 3. 删除数据库记录
            return db_manager.delete_document(kb_id=kb_id, doc_id=doc_id)
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise


# 全局实例
kb_service = KnowledgeBaseService()
