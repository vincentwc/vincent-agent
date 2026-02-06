import mimetypes
import os
import shutil
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from rag.db import db_manager
from schemas.knowledge_base import (
    DocumentResponse,
    KBCreateRequest,
    KBResponse,
    KBUpdateRequest,
)
from services.knowledge_base_service import kb_service
from utils.config_handler import config
from utils.path_tool import get_abs_path

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
            meta_info=request.meta_info,
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
    kb_id: str, request: KBUpdateRequest, tenant_id: str = "default_tenant"
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
            raise HTTPException(
                status_code=404, detail="Knowledge base not found or delete failed"
            )

        return {"status": "success", "message": "Knowledge base deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Document APIs ---

ALLOWED_EXTS = {
    ".html",
    ".xlsx",
    ".docx",
    ".xls",
    ".md",
    ".pdf",
    ".markdown",
    ".csv",
    ".txt",
}


@router.post("/{kb_id}/files/upload", response_model=DocumentResponse)
async def upload_document(
    kb_id: str, file: UploadFile = File(...), tenant_id: str = "default_tenant"
):
    kb = kb_service.get_knowledge_base(kb_id, tenant_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，仅支持: {', '.join(sorted(ALLOWED_EXTS))}",
        )

    base_dir = get_abs_path(config.chroma.get("data_path", "data"))
    kb_dir = os.path.join(base_dir, "kb", kb_id)
    os.makedirs(kb_dir, exist_ok=True)

    stored_name = file.filename
    dest_path = os.path.join(kb_dir, stored_name)
    counter = 1
    while os.path.exists(dest_path):
        name, extn = os.path.splitext(stored_name)
        stored_name = f"{name}_{counter}{extn}"
        dest_path = os.path.join(kb_dir, stored_name)
        counter += 1

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size = os.path.getsize(dest_path)
    mime = mimetypes.guess_type(dest_path)[0] or file.content_type

    doc = db_manager.create_document(
        kb_id=kb_id,
        filename=stored_name,
        stored_path=dest_path,
        size=size,
        extension=ext,
        mime_type=mime,
    )
    return DocumentResponse.model_validate(doc)


@router.get("/{kb_id}/files", response_model=List[DocumentResponse])
async def list_documents(kb_id: str, tenant_id: str = "default_tenant"):
    kb = kb_service.get_knowledge_base(kb_id, tenant_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    docs = db_manager.list_documents(kb_id)
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/{kb_id}/files/{doc_id}/download")
async def download_document(kb_id: str, doc_id: str, tenant_id: str = "default_tenant"):
    kb = kb_service.get_knowledge_base(kb_id, tenant_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    doc = db_manager.get_document(kb_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.exists(doc.stored_path):
        raise HTTPException(status_code=404, detail="File missing on server")
    return FileResponse(
        path=doc.stored_path, filename=doc.filename, media_type=doc.mime_type
    )


@router.delete("/{kb_id}/files/{doc_id}")
async def delete_document(kb_id: str, doc_id: str, tenant_id: str = "default_tenant"):
    kb = kb_service.get_knowledge_base(kb_id, tenant_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    doc = db_manager.get_document(kb_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if os.path.exists(doc.stored_path):
        try:
            os.remove(doc.stored_path)
        except Exception:
            pass
    ok = db_manager.delete_document(kb_id, doc_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete document")
    return {"status": "success"}
