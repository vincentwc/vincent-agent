from typing import List
from fastapi import APIRouter, HTTPException

from schemas.knowledge_base import (
    KBCreateRequest,
    KBUpdateRequest,
    KBResponse
)
from services.knowledge_base_service import kb_service

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

@router.post("/create", response_model=KBResponse)
async def create_knowledge_base(request: KBCreateRequest):
    """
    创建新的知识库
    """
    try:
        kb = kb_service.create_knowledge_base(
            name=request.name,
            tenant_id=request.tenant_id,
            description=request.description,
            meta_info=request.meta_info
        )
        return KBResponse.model_validate(kb)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=List[KBResponse])
async def list_knowledge_bases(tenant_id: str = "default_tenant"):
    """
    获取所有知识库列表
    """
    try:
        kbs = kb_service.list_knowledge_bases(tenant_id=tenant_id)
        return [KBResponse.model_validate(kb) for kb in kbs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{kb_id}", response_model=KBResponse)
async def get_knowledge_base(kb_id: str, tenant_id: str = "default_tenant"):
    """
    获取指定知识库详情
    """
    kb = kb_service.get_knowledge_base(kb_id, tenant_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return KBResponse.model_validate(kb)

@router.put("/{kb_id}", response_model=KBResponse)
async def update_knowledge_base(
    kb_id: str, 
    request: KBUpdateRequest, 
    tenant_id: str = "default_tenant"
):
    """
    更新知识库信息
    """
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        kb = kb_service.update_knowledge_base(kb_id, tenant_id, **update_data)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        return KBResponse.model_validate(kb)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str, tenant_id: str = "default_tenant"):
    """
    删除知识库
    """
    try:
        success = kb_service.delete_knowledge_base(kb_id, tenant_id)
        if not success:
            raise HTTPException(status_code=404, detail="Knowledge base not found or delete failed")
        
        return {"status": "success", "message": "Knowledge base deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
