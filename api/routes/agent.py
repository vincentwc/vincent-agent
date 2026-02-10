from typing import List

from fastapi import APIRouter, HTTPException

from core.codes import StatusCode
from core.response import BaseResponse
from schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentCreateRequest,
    AgentResponse,
    AgentUpdateRequest,
)
from services.agent_service import agent_service
from utils.logger_handler import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/agents", response_model=BaseResponse[AgentResponse])
async def create_agent(request: AgentCreateRequest):
    """创建智能体"""
    agent = agent_service.create_agent(
        name=request.name,
        tenant_id=request.tenant_id,
        description=request.description,
        prompt=request.prompt,
        kb_ids=request.kb_ids,
    )
    return BaseResponse.success(AgentResponse.model_validate(agent))


@router.get("/agents", response_model=BaseResponse[List[AgentResponse]])
async def list_agents(tenant_id: str = "default_tenant"):
    """获取智能体列表"""
    agents = agent_service.list_agents(tenant_id=tenant_id)
    return BaseResponse.success([AgentResponse.model_validate(a) for a in agents])


@router.get("/agents/{agent_id}", response_model=BaseResponse[AgentResponse])
async def get_agent(agent_id: str, tenant_id: str = "default_tenant"):
    """获取智能体详情"""
    agent = agent_service.get_agent(agent_id, tenant_id)
    if not agent:
        raise HTTPException(status_code=StatusCode.NOT_FOUND, detail="智能体不存在")
    return BaseResponse.success(AgentResponse.model_validate(agent))


@router.put("/agents/{agent_id}", response_model=BaseResponse[AgentResponse])
async def update_agent(
    agent_id: str, request: AgentUpdateRequest, tenant_id: str = "default_tenant"
):
    """更新智能体"""
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=StatusCode.BAD_REQUEST, detail="没有要更新的字段"
        )

    agent = agent_service.update_agent(agent_id, tenant_id, **update_data)
    if not agent:
        raise HTTPException(status_code=StatusCode.NOT_FOUND, detail="智能体不存在")
    return BaseResponse.success(AgentResponse.model_validate(agent))


@router.delete("/agents/{agent_id}", response_model=BaseResponse)
async def delete_agent(agent_id: str, tenant_id: str = "default_tenant"):
    """删除智能体"""
    success = agent_service.delete_agent(agent_id, tenant_id)
    if not success:
        raise HTTPException(status_code=StatusCode.NOT_FOUND, detail="智能体不存在")
    return BaseResponse.success(message="智能体已删除")


@router.post("/agents/{agent_id}/chat", response_model=BaseResponse[AgentChatResponse])
async def chat_agent(
    agent_id: str,
    request: AgentChatRequest,
    tenant_id: str = "default_tenant",
):
    """智能体对话"""
    try:
        answer = agent_service.chat(agent_id, request.query, tenant_id)
        return BaseResponse.success(AgentChatResponse(answer=answer))
    except ValueError as e:
        raise HTTPException(status_code=StatusCode.NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"对话处理异常: {e}")
        raise HTTPException(
            status_code=StatusCode.INTERNAL_SERVER_ERROR, detail=f"对话失败: {str(e)}"
        )
