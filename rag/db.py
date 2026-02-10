from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from rag.models import Base, KnowledgeBase, KnowledgeDocument
from utils.config_handler import config
from utils.logger_handler import get_logger

logger = get_logger(__name__)


class DBManager:
    """
    数据库管理器 (SQLAlchemy 实现)
    支持 PostgreSQL/MySQL 等商业级数据库
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化数据库连接"""
        db_url = config.database.get("url", "sqlite:///./rag.db")
        connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}

        self.engine = create_engine(db_url, connect_args=connect_args)
        # 初始化表结构
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        logger.info(f"数据库引擎已初始化: {db_url}")

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    # --- 知识库 CRUD 操作 ---

    def create_knowledge_base(
        self,
        name: str,
        tenant_id: str,
        collection_name: str,
        description: str = None,
        meta_info: dict = None,
    ) -> KnowledgeBase:
        """创建知识库"""
        session = self.get_session()
        try:
            kb = KnowledgeBase(
                name=name,
                tenant_id=tenant_id,
                collection_name=collection_name,
                description=description,
                meta_info=meta_info or {},
            )
            session.add(kb)
            session.commit()
            session.refresh(kb)
            return kb
        except Exception as e:
            session.rollback()
            logger.error(f"创建知识库失败: {e}")
            raise
        finally:
            session.close()

    def get_knowledge_base(self, kb_id: str, tenant_id: str) -> Optional[KnowledgeBase]:
        """根据 ID 获取知识库"""
        session = self.get_session()
        try:
            return (
                session.query(KnowledgeBase)
                .filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == tenant_id)
                .first()
            )
        finally:
            session.close()

    def get_knowledge_base_by_name(
        self, name: str, tenant_id: str
    ) -> Optional[KnowledgeBase]:
        """根据名称获取知识库"""
        session = self.get_session()
        try:
            return (
                session.query(KnowledgeBase)
                .filter(
                    KnowledgeBase.name == name, KnowledgeBase.tenant_id == tenant_id
                )
                .first()
            )
        finally:
            session.close()

    def list_knowledge_bases(
        self, tenant_id: str = None, limit: int = 100, offset: int = 0
    ) -> List[KnowledgeBase]:
        """获取知识库列表"""
        session = self.get_session()
        try:
            query = session.query(KnowledgeBase)
            if tenant_id:
                query = query.filter(KnowledgeBase.tenant_id == tenant_id)
            return query.limit(limit).offset(offset).all()
        finally:
            session.close()

    def update_knowledge_base(
        self, kb_id: str, tenant_id: str, **kwargs
    ) -> Optional[KnowledgeBase]:
        """更新知识库信息"""
        session = self.get_session()
        try:
            kb = (
                session.query(KnowledgeBase)
                .filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == tenant_id)
                .first()
            )
            if not kb:
                return None

            for key, value in kwargs.items():
                if hasattr(kb, key):
                    setattr(kb, key, value)
            # 处理 meta_info 更新
            if "meta_info" in kwargs:
                kb.meta_info.update(kwargs["meta_info"] or {})

            session.commit()
            session.refresh(kb)
            return kb
        except Exception as e:
            session.rollback()
            logger.error(f"更新知识库失败: {e}")
            raise
        finally:
            session.close()

    def delete_knowledge_base(self, kb_id: str, tenant_id: str) -> bool:
        """删除知识库"""
        session = self.get_session()
        try:
            kb = (
                session.query(KnowledgeBase)
                .filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == tenant_id)
                .first()
            )
            if not kb:
                return False

            session.query(KnowledgeDocument).filter(
                KnowledgeDocument.kb_id == kb_id
            ).delete()
            session.delete(kb)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"删除知识库失败: {e}")
            raise
        finally:
            session.close()

    # --- 文档 CRUD 操作 ---

    def create_document(
        self,
        kb_id: str,
        filename: str,
        stored_path: str,
        size: int,
        extension: str,
        mime_type: str = None,
        md5: str = None,
    ) -> KnowledgeDocument:
        session = self.get_session()
        try:
            doc = KnowledgeDocument(
                kb_id=kb_id,
                filename=filename,
                stored_path=stored_path,
                size=size,
                extension=extension,
                mime_type=mime_type,
                md5=md5,
            )
            session.add(doc)
            session.commit()
            session.refresh(doc)
            return doc
        except Exception as e:
            session.rollback()
            logger.error(f"创建文档失败: {e}")
            raise
        finally:
            session.close()

    def check_document_exists(self, kb_id: str, md5: str) -> bool:
        """检查知识库中是否存在相同MD5的文档"""
        session = self.get_session()
        try:
            return (
                session.query(KnowledgeDocument)
                .filter(KnowledgeDocument.kb_id == kb_id, KnowledgeDocument.md5 == md5)
                .first()
                is not None
            )
        finally:
            session.close()

    def list_documents(self, kb_id: str) -> List[KnowledgeDocument]:
        session = self.get_session()
        try:
            return (
                session.query(KnowledgeDocument)
                .filter(KnowledgeDocument.kb_id == kb_id)
                .order_by(KnowledgeDocument.created_at.desc())
                .all()
            )
        finally:
            session.close()

    def get_document(self, kb_id: str, doc_id: str) -> Optional[KnowledgeDocument]:
        session = self.get_session()
        try:
            return (
                session.query(KnowledgeDocument)
                .filter(
                    KnowledgeDocument.id == doc_id, KnowledgeDocument.kb_id == kb_id
                )
                .first()
            )
        finally:
            session.close()

    def update_document_status(
        self, kb_id: str, doc_id: str, status: str, error_msg: str = None
    ) -> bool:
        """更新文档状态"""
        session = self.get_session()
        try:
            doc = (
                session.query(KnowledgeDocument)
                .filter(
                    KnowledgeDocument.id == doc_id, KnowledgeDocument.kb_id == kb_id
                )
                .first()
            )
            if not doc:
                return False

            doc.status = status
            if error_msg:
                doc.error_msg = error_msg

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"更新文档状态失败: {e}")
            return False
        finally:
            session.close()

    def delete_document(self, kb_id: str, doc_id: str) -> bool:
        session = self.get_session()
        try:
            doc = (
                session.query(KnowledgeDocument)
                .filter(
                    KnowledgeDocument.id == doc_id, KnowledgeDocument.kb_id == kb_id
                )
                .first()
            )
            if not doc:
                return False
            session.delete(doc)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"删除文档失败: {e}")
            raise
        finally:
            session.close()


# 全局数据库实例
db_manager = DBManager()


# if __name__ == "__main__":
#     db_manager._init_engine()
