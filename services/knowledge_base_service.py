import os
import shutil
import uuid
from typing import List, Optional

from fastapi import BackgroundTasks, HTTPException, UploadFile

from core.codes import StatusCode
from database.db import db_manager
from database.models import KnowledgeBase, KnowledgeDocument
from database.vector_store import VectoreStoreService
from utils.config_handler import config
from utils.file_handler import get_file_md5_hex
from utils.logger_handler import get_logger
from utils.path_tool import get_abs_path

logger = get_logger(__name__)
vector_store = VectoreStoreService()


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
            logger.info(f"创建知识库成功: {name} (ID: {kb.id})")
            return kb
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
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
                logger.info(f"更新知识库成功: {kb.name} (ID: {kb.id})")
            return kb
        except Exception as e:
            logger.error(f"更新知识库失败: {e}")
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
                # 调用 Chroma 删除对应的 Collection 数据 (通过 metadata 过滤)
                vector_store.delete_knowledge_base(kb_id)
                logger.info(f"删除知识库成功: {kb.name} (ID: {kb_id})")

            return success
        except Exception as e:
            logger.error(f"删除知识库失败: {e}")
            raise

    # --- Document Management ---

    def upload_document(
        self, kb_id: str, file: UploadFile, background_tasks: BackgroundTasks = None
    ) -> KnowledgeDocument:
        """
        上传文档到知识库
        """
        try:
            # 0. 校验文件类型
            allowed_types = config.chroma.get("allowed_file_type", ["pdf", "txt"])
            # 确保配置中的类型都是小写，并且带点（如果配置没有带点的话）
            # 这里假设配置是 ["pdf", "txt"]

            # 获取文件扩展名 (包含点, 如 .pdf)
            _, ext = os.path.splitext(file.filename)
            ext = ext.lower().lstrip(".")  # 去掉点，统一比较

            if ext not in allowed_types:
                raise HTTPException(
                    status_code=StatusCode.BAD_REQUEST,
                    detail=f"不支持的文件类型: {ext}. 允许的类型: {allowed_types}",
                )

            # 1. 确定存储路径
            # 结构: data/uploads/{kb_id}/{filename}
            upload_dir = get_abs_path(f"data/uploads/{kb_id}")
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, file.filename)

            # 2. 保存文件
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # 3. 计算 MD5 并查重
            md5 = get_file_md5_hex(file_path)
            if md5 and db_manager.check_document_exists(kb_id, md5):
                # 如果已存在，删除刚上传的文件并抛出异常
                os.remove(file_path)
                raise HTTPException(
                    status_code=StatusCode.BAD_REQUEST,
                    detail=f"文档 {file.filename} 已存在，请勿重复上传",
                )

            # 4. 获取文件信息
            size = os.path.getsize(file_path)
            extension = os.path.splitext(file.filename)[1].lower()
            mime_type = file.content_type

            # 5. 写入数据库
            doc = db_manager.create_document(
                kb_id=kb_id,
                filename=file.filename,
                stored_path=file_path,
                size=size,
                extension=extension,
                mime_type=mime_type,
                md5=md5,
            )

            # 6. 触发向量化任务
            if background_tasks:
                background_tasks.add_task(
                    vector_store.add_document,  # <--- 要执行的函数 (不要加括号调用)
                    kb_id=kb_id,  # <--- 参数 1
                    doc_id=doc.id,  # <--- 参数 2
                    file_path=file_path,  # <--- 参数 3
                )
            else:
                # 如果没有提供 background_tasks，则同步执行 (可能会阻塞)
                logger.warning("未提供 BackgroundTasks，正在同步执行向量化...")
                vector_store.add_document(
                    kb_id=kb_id, doc_id=doc.id, file_path=file_path
                )

            logger.info(f"文档上传成功: {file.filename} 到知识库: {kb_id}")
            return doc
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"文档上传失败: {e}")
            raise

    def download_document(self, kb_id: str, doc_id: str) -> str:
        """
        获取文档下载路径
        """
        doc = db_manager.get_document(kb_id=kb_id, doc_id=doc_id)
        if not doc:
            raise HTTPException(status_code=StatusCode.NOT_FOUND, detail="文档未找到")

        if not os.path.exists(doc.stored_path):
            raise HTTPException(
                status_code=StatusCode.NOT_FOUND, detail="服务器上找不到文件"
            )

        return doc.stored_path

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
                    logger.warning(f"删除文件失败 {doc.stored_path}: {e}")

            # 3. 删除数据库记录
            if db_manager.delete_document(kb_id=kb_id, doc_id=doc_id):
                # 4. 删除向量库记录
                vector_store.delete_document(kb_id=kb_id, doc_id=doc_id)
                return True
            return False
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise


# 全局实例
kb_service = KnowledgeBaseService()
