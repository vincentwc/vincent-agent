"""
路径工具类
"""

from pathlib import Path


def get_project_root_dir() -> str:
    """
    获取项目根目录
    """
    # 假设 utils 目录在项目根目录下，所以向上两级
    return str(Path(__file__).resolve().parent.parent)


def get_abs_path(relative_path: str) -> str:
    """
    获取绝对路径
    """
    return str(Path(get_project_root_dir()) / relative_path)
