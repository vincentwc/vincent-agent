import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    SQLAlchemy 声明式基类。
    """
    pass


class AgentKBAssociation(Base):
    """
    智能体与知识库的关联表 (多对多)。

    Attributes:
        agent_id (str): 智能体ID。
        kb_id (str): 知识库ID。
    """
    __tablename__ = "agent_kb_association"
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id"), primary_key=True
    )
    kb_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id"), primary_key=True
    )


class Agent(Base):
    """
    智能体 (Agent) 模型。
    用于定义聊天助手的配置信息，包括名称、模型参数和关联知识库。

    Attributes:
        id (str): 唯一标识符。
        name (str): 智能体名称。
        tenant_id (str): 租户ID。
        description (str): 描述信息。
        model_name (str): 使用的LLM模型名称。
        prompt (str): 系统提示词。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
        knowledge_bases (List[KnowledgeBase]): 关联的知识库列表。
    """
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="助手名称")
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="租户ID"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, comment="描述信息")
    model_name: Mapped[str] = mapped_column(
        String(100), default="gpt-3.5-turbo", comment="使用的LLM模型"
    )
    prompt: Mapped[Optional[str]] = mapped_column(Text, comment="系统提示词")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    # Many-to-Many relationship
    knowledge_bases: Mapped[List["KnowledgeBase"]] = relationship(
        secondary="agent_kb_association", back_populates="agents"
    )

    def __repr__(self) -> str:
        return f"<Agent(name='{self.name}')>"


class KnowledgeBase(Base):
    """
    知识库 (KnowledgeBase) 模型。
    管理知识库元数据和配置。

    Attributes:
        id (str): 唯一标识符。
        name (str): 知识库名称。
        tenant_id (str): 租户ID。
        collection_name (str): 向量数据库中的集合名称。
        description (str): 描述信息。
        meta_info (dict): 扩展元数据。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
        agents (List[Agent]): 关联的智能体列表。
    """
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="知识库名称")
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="租户ID"
    )
    collection_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="Chroma集合名称"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, comment="描述信息")
    meta_info: Mapped[Optional[dict]] = mapped_column(
        JSON, default={}, comment="扩展元数据(MongoDB-like)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    # Reverse relationship
    agents: Mapped[List["Agent"]] = relationship(
        secondary="agent_kb_association", back_populates="knowledge_bases"
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeBase(name='{self.name}', collection='{self.collection_name}')>"
        )


class KnowledgeDocument(Base):
    """
    知识文档 (KnowledgeDocument) 模型。
    记录上传的文件及其处理状态。

    Attributes:
        id (str): 唯一标识符。
        kb_id (str): 所属知识库ID。
        filename (str): 文件名。
        extension (str): 文件扩展名。
        mime_type (str): MIME类型。
        size (int): 文件大小(字节)。
        md5 (str): 文件MD5哈希值。
        status (str): 处理状态 (pending/running/completed/failed)。
        error_msg (str): 错误信息。
        stored_path (str): 文件存储路径。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
    """
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    kb_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    md5: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="文件MD5"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="向量化状态: pending/running/completed/failed",
    )
    error_msg: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
