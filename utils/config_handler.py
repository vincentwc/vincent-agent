"""
配置文件处理工具类
"""

import yaml

from utils.path_tool import get_abs_path


class Config:
    """
    全局配置类 (单例模式/懒加载)

    使用方法:
    from utils.config_handler import config

    print(config.rag)
    print(config.agent)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化配置缓存"""
        self._rag = None
        self._chroma = None
        self._agent = None
        self._prompts = None
        self._database = None

    def _load_yaml(self, filename: str) -> dict:
        """通用 YAML 加载函数"""
        config_path = get_abs_path(f"config/{filename}")
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            # 允许文件不存在，返回空字典
            return {}
        except Exception as e:
            # 记录错误但不要崩溃，打印控制台
            print(f"Warning: Failed to load config {filename}: {e}")
            return {}

    @property
    def rag(self) -> dict:
        if self._rag is None:
            self._rag = self._load_yaml("rag.yaml")
        return self._rag

    @property
    def chroma(self) -> dict:
        if self._chroma is None:
            self._chroma = self._load_yaml("chroma.yaml")
        return self._chroma

    @property
    def agent(self) -> dict:
        if self._agent is None:
            self._agent = self._load_yaml("agent.yaml")
        return self._agent

    @property
    def prompts(self) -> dict:
        if self._prompts is None:
            self._prompts = self._load_yaml("prompts.yaml")
        return self._prompts

    @property
    def database(self) -> dict:
        if self._database is None:
            self._database = self._load_yaml("database.yaml")
        return self._database


# 全局单例对象
config = Config()

# if __name__ == "__main__":
#     # 测试代码
#     print("RAG Config:", config.rag)
#     print("Agent Config:", config.agent)
#     print("Prompts Config:", config.prompts)
#     print("Chroma Config:", config.chroma)
#     print("Agent Config:", config.agent["chat_model_name"])
#     a = Config()
#     b = Config()
#     print(a is b)
