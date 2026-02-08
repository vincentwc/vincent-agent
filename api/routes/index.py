
import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from utils.path_tool import get_abs_path

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def read_root():
    """返回主页"""
    static_dir = get_abs_path("static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>请在 static 目录下创建 index.html</h1>"
