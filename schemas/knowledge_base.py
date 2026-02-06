from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class KBBase(BaseModel):
    """知识库基础模型"""
    name: str
    description: Optional[str] = None
    meta_info: Optional[dict] = {}

class KBCreateRequest(KBBase):
    """创建知识库请求模型"""
    tenant_id: str = "default_tenant"  # 商业化租户ID

class KBUpdateRequest(BaseModel):
    """知识库更新模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    meta_info: Optional[dict] = None

class KBResponse(KBBase):
    """知识库响应模型"""
    id: str
    tenant_id: str
    collection_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
