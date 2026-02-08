from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

from core.codes import StatusCode

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    code: int = StatusCode.SUCCESS
    message: str = "操作成功"
    data: Optional[T] = None

    @classmethod
    def success(cls, data: T = None, message: str = None):
        if message is None:
            message = StatusCode.SUCCESS.description
        return cls(code=StatusCode.SUCCESS, message=message, data=data)

    @classmethod
    def error(
        cls,
        code: int = StatusCode.SERVER_ERROR,
        message: str = None,
        data: Any = None,
    ):
        if message is None:
            # 尝试从 StatusCode 获取描述
            try:
                if isinstance(code, StatusCode):
                    message = code.description
                else:
                    message = StatusCode(code).description
            except (ValueError, AttributeError):
                message = "未知错误"

        return cls(code=code, message=message, data=data)
