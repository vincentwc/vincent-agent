import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class KnowledgeBase(Base):
    """
    知识库元数据模型
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

    def __repr__(self) -> str:
        return (
            f"<KnowledgeBase(name='{self.name}', collection='{self.collection_name}')>"
        )
