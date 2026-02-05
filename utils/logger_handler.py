"""
日志处理工具类
"""

import os
import logging
from datetime import datetime

from utils.path_tool import get_abs_path


# 日志保存的根目录
LOG_ROOT_DIR = get_abs_path("logs")

# 确保日志目录存在
os.makedirs(LOG_ROOT_DIR, exist_ok=True)

# 日志格式 日志时间 - 日志名称 - 日志级别 - 文件名:行号 - 日志消息
DEFAULT_LOG_FORMAT = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)


def get_logger(
    logger_name: str = "agent",
    log_file: str = None,
    console_log_level: int = logging.INFO,
    print_console_log: bool = True,
    log_level: int = logging.DEBUG,
) -> logging.Logger:
    """
    获取日志记录器
    Args:
        logger_name: 日志记录器名称，默认agent
        log_file: 日志文件名，默认None
        console_log_level: 控制台日志级别，默认INFO
        print_console_log: 是否在控制台打印日志，默认True
        log_level: 日志级别，默认DEBUG
    Returns:
        logging.Logger: 日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # 如果记录器已经有处理器，直接返回
    if logger.handlers:
        return logger

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)
    console_handler.setLevel(console_log_level)
    if print_console_log:
        logger.addHandler(console_handler)

    # 日志文件处理器
    if not log_file:
        # 如果没有指定日志文件名，默认使用 日志记录器名称_日期.log
        log_file = os.path.join(
            LOG_ROOT_DIR, f"{logger_name}_{datetime.now().strftime('%Y%m%d')}.log"
        )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)
    logger.addHandler(file_handler)

    return logger


if __name__ == "__main__":
    logger = get_logger()
    logger.debug("这是一条debug日志")
    logger.info("这是一条info日志")
    logger.warning("这是一条warning日志")
    logger.error("这是一条error日志")
    logger.critical("这是一条critical日志")
    print(get_abs_path(__name__))
