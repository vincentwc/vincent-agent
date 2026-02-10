from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_serializer

from schemas.knowledge_base import KBResponse


class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    prompt: Optional[str] = None
    model_config = ConfigDict(protected_namespaces=())


class AgentCreateRequest(AgentBase):
    tenant_id: str = "default_tenant"
    kb_ids: List[str] = []
    model_config = ConfigDict(protected_namespaces=())


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    kb_ids: Optional[List[str]] = None
    model_config = ConfigDict(protected_namespaces=())


class AgentResponse(AgentBase):
    id: str
    tenant_id: str
    model_name: str
    created_at: datetime
    updated_at: datetime
    knowledge_bases: List[KBResponse] = []

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
