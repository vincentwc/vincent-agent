import os
import shutil

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from api.routes import knowledge_base
from rag.vector_store import VectoreStoreService
from utils.config_handler import config
from utils.logger_handler import get_logger
from utils.path_tool import get_abs_path
from core.exception import register_exception_handlers

logger = get_logger(__name__)

app = FastAPI(title="Vincent Agent API")

# Register Global Exception Handlers
register_exception_handlers(app)

# Include Routers
app.include_router(knowledge_base.router)

# 挂载静态文件目录，用于访问 css/js 等资源（如果将来有的话）
# 注意：我们需要先确保 static 目录存在
static_dir = get_abs_path("static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """返回主页"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>请在 static 目录下创建 index.html</h1>"


@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    文件上传接口
    1. 保存文件到 data 目录
    2. 触发向量化后台任务
    """
    try:
        # 1. 确定保存路径
        data_path = get_abs_path(config.chroma.get("data_path", "data"))
        if not os.path.exists(data_path):
            os.makedirs(data_path)

        file_location = os.path.join(data_path, file.filename)

        # 2. 保存文件
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"文件已上传并保存至: {file_location}")

        # 3. 触发向量化处理 (后台任务)
        vector_service = VectoreStoreService()
        background_tasks.add_task(vector_service.process_file, file_location)

        return {
            "filename": file.filename,
            "status": "success",
            "message": "文件已上传，正在后台处理中...",
        }

    except Exception as e:
        logger.error(f"文件上传处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
