from abc import ABC, abstractmethod
from typing import Optional, Union

from langchain_community.chat_models.tongyi import BaseChatModel, ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.embeddings import Embeddings

from utils.config_handler import config
from utils.logger_handler import get_logger

logger = get_logger(__name__)


class BaseModelFactory(ABC):
    """
    基础模型工厂抽象基类。
    """

    @abstractmethod
    def get_model(self) -> Union[BaseChatModel, Embeddings, None]:
        """
        获取模型实例。

        Returns:
            Union[BaseChatModel, Embeddings, None]: 模型实例。
        """
        pass


class ChatModelFactory(BaseModelFactory):
    """
    聊天模型工厂类。
    """

    def get_model(self) -> Optional[BaseChatModel]:
        """
        获取聊天模型实例。

        Returns:
            Optional[BaseChatModel]: 聊天模型实例，如果初始化失败可能抛出异常。

        Raises:
            ValueError: 如果配置中未指定模型名称。
        """
        model_name = config.agent.get("chat_model_name", "")
        if not model_name:
            logger.error("配置中未找到聊天模型名称。")
            raise ValueError("Chat model name is required.")

        try:
            logger.info(f"正在初始化 ChatTongyi 模型: {model_name}")
            return ChatTongyi(model=model_name)
        except Exception as e:
            logger.error(f"初始化 ChatTongyi 失败: {e}")
            raise


class EmbeddingModelFactory(BaseModelFactory):
    """
    嵌入模型工厂类。
    """

    def get_model(self) -> Optional[Embeddings]:
        """
        获取嵌入模型实例。

        Returns:
            Optional[Embeddings]: 嵌入模型实例。

        Raises:
            ValueError: 如果配置中未指定模型名称。
        """
        model_name = config.agent.get("embedding_model_name", "")
        if not model_name:
            logger.error("配置中未找到嵌入模型名称。")
            raise ValueError("Embedding model name is required.")

        try:
            logger.info(f"正在初始化 DashScopeEmbeddings 模型: {model_name}")
            return DashScopeEmbeddings(model=model_name)
        except Exception as e:
            logger.error(f"初始化 DashScopeEmbeddings 失败: {e}")
            raise


# 导出工厂实例
chat_model_factory = ChatModelFactory()
embedding_model_factory = EmbeddingModelFactory()
