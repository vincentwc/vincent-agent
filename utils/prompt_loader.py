from utils.config_handler import config
from utils.logger_handler import get_logger
from utils.path_tool import get_abs_path

logger = get_logger(__name__)


def load_system_prompt() -> str:
    """
    加载系统提示词
    Returns:
        str: 系统提示词
    """
    # 从配置文件中加载系统提示词
    try:
        system_prompt_path = get_abs_path(config.prompts.get("main_prompt_path", ""))
    except KeyError as e:
        logger.error(f"[load_system_prompt]解析系统提示词路径文件失败: {str(e)}")
        raise

    try:
        with open(system_prompt_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except Exception as e:
        logger.error(
            f"[load_system_prompt]系统提示词文件{system_prompt_path}解析失败: {str(e)}"
        )
        raise


def load_rag_prompts() -> str:
    """
    加载RAG默认提示词[字符串]
    Returns:
        str: RAG提示词
    """
    # 从配置文件中加载RAG提示词
    try:
        rag_prompts_path = get_abs_path(config.prompts.get("rag_summarize_prompt_path", ""))
    except KeyError as e:
        logger.error(f"[load_rag_prompts]解析RAG提示词路径文件失败: {str(e)}")
        raise

    try:
        with open(rag_prompts_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except Exception as e:
        logger.error(
            f"[load_rag_prompts]RAG提示词文件{rag_prompts_path}解析失败: {str(e)}"
        )
        raise
      

def load_report_prompts() -> str:
    """
    加载RAG报告提示词[字符串]
    Returns:
        str: RAG报告提示词  
    """
    # 从配置文件中加载RAG报告提示词
    try:
        report_prompts_path = get_abs_path(config.prompts.get("report_prompt_path", ""))
    except KeyError as e:
        logger.error(f"[load_report_prompts]解析RAG报告提示词路径文件失败: {str(e)}")
        raise

    try:
        with open(report_prompts_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except Exception as e:
        logger.error(
            f"[load_report_prompts]RAG报告提示词文件{report_prompts_path}解析失败: {str(e)}"
        )
        raise
      
      
# if __name__ == "__main__":
    # print(load_system_prompt())
    # print(load_rag_prompts())
    # print(load_report_prompts())