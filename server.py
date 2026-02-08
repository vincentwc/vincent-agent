import os
import shutil

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from api.routes import index, knowledge_base
from core.exception import register_exception_handlers
from utils.config_handler import config
from utils.logger_handler import get_logger
from utils.path_tool import get_abs_path

logger = get_logger(__name__)

app = FastAPI(title="Vincent Agent API")

# Register Global Exception Handlers
register_exception_handlers(app)

# Include Routers
app.include_router(knowledge_base.router, prefix="/kb", tags=["Knowledge Base"])
app.include_router(index.router, tags=["Web"])

# 挂载静态文件目录，用于访问 css/js 等资源（如果将来有的话）
# 注意：我们需要先确保 static 目录存在
static_dir = get_abs_path("static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
