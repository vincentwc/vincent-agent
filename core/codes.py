from enum import Enum


class StatusCode(int, Enum):
    """
    统一状态码定义
    继承 int 以兼容 FastAPI 的 status_code 检查
    支持 (code, description) 的定义方式
    """

    def __new__(cls, value, description):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj

    # 标准 HTTP 状态码
    SUCCESS = (200, "操作成功")
    BAD_REQUEST = (400, "请求参数错误")
    UNAUTHORIZED = (401, "身份验证失败")
    FORBIDDEN = (403, "权限不足")
    NOT_FOUND = (404, "资源未找到")
    METHOD_NOT_ALLOWED = (405, "请求方法不允许")
    VALIDATION_ERROR = (422, "参数校验失败")
    INTERNAL_SERVER_ERROR = (500, "系统内部错误")

    # 业务错误码 (5000-5999)
    DB_ERROR = (5001, "数据库操作异常")
    FILE_UPLOAD_ERROR = (5002, "文件上传失败")
    FILE_PARSE_ERROR = (5003, "文件解析失败")
    VECTOR_STORE_ERROR = (5004, "向量存储异常")
