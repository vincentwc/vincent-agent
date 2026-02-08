import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.codes import StatusCode
from core.response import BaseResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=BaseResponse.error(
                code=exc.status_code, message=exc.detail
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=StatusCode.VALIDATION_ERROR,
            content=BaseResponse.error(
                code=StatusCode.VALIDATION_ERROR, data=str(exc)
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"全局异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=StatusCode.SERVER_ERROR,
            content=BaseResponse.error(
                code=StatusCode.SERVER_ERROR, data=str(exc)
            ).model_dump(),
        )
