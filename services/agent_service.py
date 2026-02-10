from typing import List, Optional

from database.db import db_manager
from database.models import Agent
from utils.config_handler import config
from utils.logger_handler import get_logger

logger = get_logger(__name__)


class AgentService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentService, cls).__new__(cls)
        return cls._instance

    def create_agent(
        self,
        name: str,
        tenant_id: str,
        description: str = None,
        prompt: str = None,
        kb_ids: List[str] = None,
    ) -> Agent:
        """创建智能体"""
        # 强制使用配置中的模型
        final_model_name = config.agent.get("chat_model_name", "gpt-3.5-turbo")

        return db_manager.create_agent(
            name=name,
            tenant_id=tenant_id,
            description=description,
            model_name=final_model_name,
            prompt=prompt,
            kb_ids=kb_ids,
        )

    def get_agent(self, agent_id: str, tenant_id: str) -> Optional[Agent]:
        """获取智能体详情"""
        return db_manager.get_agent(agent_id, tenant_id)

    def list_agents(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> List[Agent]:
        """获取智能体列表"""
        return db_manager.list_agents(tenant_id, limit, offset)

    def update_agent(self, agent_id: str, tenant_id: str, **kwargs) -> Optional[Agent]:
        """更新智能体"""
        return db_manager.update_agent(agent_id, tenant_id, **kwargs)

    def delete_agent(self, agent_id: str, tenant_id: str) -> bool:
        """删除智能体"""
        return db_manager.delete_agent(agent_id, tenant_id)


agent_service = AgentService()
