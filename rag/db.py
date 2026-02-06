from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from rag.models import Base, KnowledgeBase
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
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._init_engine()
        self._initialized = True

    def _init_engine(self):
        """初始化数据库引擎"""
        db_config = config.database
        db_url = db_config.get("url", "sqlite:///data/rag.db")

        # 引擎配置
        engine_kwargs = {
            "echo": db_config.get("echo", False),
        }

        # 连接池配置 (SQLite 不支持 pool_size)
        if "sqlite" not in db_url:
            engine_kwargs["pool_size"] = db_config.get("pool_size", 5)
            engine_kwargs["max_overflow"] = db_config.get("max_overflow", 10)

        try:
            self.engine = create_engine(db_url, **engine_kwargs)

            # 创建所有表 (如果不存在)
            # 在生产环境中，建议使用 Alembic 进行迁移管理
            Base.metadata.create_all(self.engine)

            # 创建线程安全的 Session 工厂
            self.SessionLocal = scoped_session(
                sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            )

            logger.info(
                f"数据库引擎已初始化: {db_url.split('@')[-1] if '@' in db_url else db_url}"
            )
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

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

    def get_knowledge_base_by_name(self, name: str, tenant_id: str) -> Optional[KnowledgeBase]:
        """根据名称获取知识库"""
        session = self.get_session()
        try:
            return (
                session.query(KnowledgeBase)
                .filter(KnowledgeBase.name == name, KnowledgeBase.tenant_id == tenant_id)
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

    def update_knowledge_base(self, kb_id: str, tenant_id: str, **kwargs) -> Optional[KnowledgeBase]:
        """更新知识库信息"""
        session = self.get_session()
        try:
            kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == tenant_id).first()
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
            kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == tenant_id).first()
            if not kb:
                return False

            session.delete(kb)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"删除知识库失败: {e}")
            raise
        finally:
            session.close()


# 全局数据库实例
db_manager = DBManager()


# if __name__ == "__main__":
#     db_manager._init_engine()
