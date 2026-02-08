import os
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from core.codes import StatusCode
from core.response import BaseResponse
from schemas.knowledge_base import (
    DocumentResponse,
    KBCreateRequest,
    KBResponse,
    KBUpdateRequest,
)
from services.knowledge_base_service import kb_service
from utils.config_handler import config

router = APIRouter()


@router.get("/config", response_model=BaseResponse)
async def get_kb_config():
    """
    获取知识库配置（如允许的文件类型）
    """
    allowed_types = config.chroma.get("allowed_file_type", ["pdf", "txt"])
    return BaseResponse.success(data={"allowed_file_types": allowed_types})


@router.post("/create", response_model=BaseResponse[KBResponse])
async def create_knowledge_base(request: KBCreateRequest):
    """
    创建新的知识库
    """
    kb = kb_service.create_knowledge_base(
        name=request.name,
        tenant_id=request.tenant_id,
        description=request.description,
        meta_info=request.meta_info,
    )
    return BaseResponse.success(KBResponse.model_validate(kb))


@router.get("/list", response_model=BaseResponse[List[KBResponse]])
async def list_knowledge_bases(tenant_id: str = "default_tenant"):
    """
    获取所有知识库列表
    """
    kbs = kb_service.list_knowledge_bases(tenant_id=tenant_id)
    return BaseResponse.success([KBResponse.model_validate(kb) for kb in kbs])


@router.get("/{kb_id}", response_model=BaseResponse[KBResponse])
async def get_knowledge_base(kb_id: str, tenant_id: str = "default_tenant"):
    """
    获取指定知识库详情
    """
    kb = kb_service.get_knowledge_base(kb_id, tenant_id)
    if not kb:
        raise HTTPException(status_code=StatusCode.NOT_FOUND, detail="知识库不存在")    
    return BaseResponse.success(KBResponse.model_validate(kb))


@router.put("/{kb_id}", response_model=BaseResponse[KBResponse])
async def update_knowledge_base(
    kb_id: str, request: KBUpdateRequest, tenant_id: str = "default_tenant"
):
    """
    更新知识库信息
    """
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=StatusCode.BAD_REQUEST, detail="没有要更新的字段"
        )

    kb = kb_service.update_knowledge_base(kb_id, tenant_id, **update_data)
    if not kb:
        raise HTTPException(status_code=StatusCode.NOT_FOUND, detail="未找到知识库")
    return BaseResponse.success(KBResponse.model_validate(kb))


@router.delete("/{kb_id}", response_model=BaseResponse)
async def delete_knowledge_base(kb_id: str, tenant_id: str = "default_tenant"):
    """
    删除知识库
    """
    success = kb_service.delete_knowledge_base(kb_id, tenant_id)
    if not success:
        raise HTTPException(
            status_code=StatusCode.NOT_FOUND,
            detail="知识库不存在或删除失败",
        )

    return BaseResponse.success(message="知识库已删除")


@router.post("/{kb_id}/documents/upload", response_model=BaseResponse[DocumentResponse])
async def upload_document(kb_id: str, file: UploadFile = File(...)):
    """
    上传文档到知识库
    """
    doc = kb_service.upload_document(kb_id, file)
    return BaseResponse.success(DocumentResponse.model_validate(doc))


@router.get("/{kb_id}/documents", response_model=BaseResponse[List[DocumentResponse]])
async def list_documents(kb_id: str):
    """
    获取知识库下的文档列表
    """
    docs = kb_service.list_documents(kb_id)
    return BaseResponse.success([DocumentResponse.model_validate(doc) for doc in docs])


@router.get("/{kb_id}/documents/{doc_id}/download", response_class=FileResponse)
async def download_document(kb_id: str, doc_id: str):
    """
    下载文档
    """
    file_path = kb_service.download_document(kb_id, doc_id)
    # 获取文件名
    filename = os.path.basename(file_path)
    return FileResponse(
        path=file_path, filename=filename, media_type="application/octet-stream"
    )


@router.delete("/{kb_id}/documents/{doc_id}", response_model=BaseResponse)
async def delete_document(kb_id: str, doc_id: str):
    """
    删除文档
    """
    success = kb_service.delete_document(kb_id, doc_id)
    if not success:
        raise HTTPException(status_code=StatusCode.NOT_FOUND, detail="文档未找到")
    return BaseResponse.success(message="文档已删除")
