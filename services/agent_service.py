from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from database.db import db_manager
from database.models import Agent
from database.vector_store import VectoreStoreService
from model.factory import chat_model_factory
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

    def chat(self, agent_id: str, query: str, tenant_id: str = "default_tenant") -> str:
        """智能体对话"""
        agent = self.get_agent(agent_id, tenant_id)
        if not agent:
            raise ValueError("Agent not found")

        # 1. 检索上下文
        context = ""
        # 注意：这里假设 agent.knowledge_bases 已经被 eager loading 加载
        kb_ids = [kb.id for kb in agent.knowledge_bases]

        if kb_ids:
            try:
                vector_store = VectoreStoreService()
                # Chroma filter syntax: {"field": {"$in": [values]}}
                filter_rule = {"kb_id": {"$in": kb_ids}}

                # 使用标准的 similarity 模式，避免因分数转换导致的 UserWarning
                retriever = vector_store.get_retriever(
                    k=config.chroma.get("k", 3),
                    filter=filter_rule,
                )
                docs = retriever.invoke(query)
                if docs:
                    context = "\n\n".join([doc.page_content for doc in docs])
                    logger.info(f"Retrieved {len(docs)} documents for context.")
            except Exception as e:
                logger.error(f"检索知识库失败: {e}")

        # 2. 构建提示词
        base_prompt = agent.prompt or "You are a helpful assistant."
        if context:
            system_content = f"{base_prompt}\n\n基于以下上下文回答问题:\n{context}"
        else:
            system_content = base_prompt

        messages = [SystemMessage(content=system_content), HumanMessage(content=query)]

        # 3. 调用模型
        try:
            model = chat_model_factory.get_model()
            response = model.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            raise


agent_service = AgentService()
