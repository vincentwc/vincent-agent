from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class KBBase(BaseModel):
    name: str
    description: Optional[str] = None
    meta_info: Optional[dict] = {}

class KBCreateRequest(KBBase):
    tenant_id: str = "default_tenant"  # 商业化租户ID

class KBUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    meta_info: Optional[dict] = None

class KBResponse(KBBase):
    id: str
    tenant_id: str
    collection_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    extension: str
    mime_type: Optional[str] = None
    size: int
    stored_path: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
