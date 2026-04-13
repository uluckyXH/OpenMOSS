"""
应用级业务异常定义。
"""


class BusinessError(Exception):
    """可安全返回给客户端的业务异常。"""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class NotFoundError(BusinessError):
    """资源不存在。"""

    def __init__(self, detail: str):
        super().__init__(detail, status_code=404)


class ValidationError(BusinessError):
    """请求参数或业务输入非法。"""

    def __init__(self, detail: str):
        super().__init__(detail, status_code=400)


class ConflictError(BusinessError):
    """资源状态冲突。"""

    def __init__(self, detail: str):
        super().__init__(detail, status_code=409)


class ForbiddenError(BusinessError):
    """当前操作不被允许。"""

    def __init__(self, detail: str):
        super().__init__(detail, status_code=403)


class AdminQueryError(BusinessError):
    """管理端查询业务异常。"""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail, status_code=status_code)


class AdminInvalidQueryError(AdminQueryError):
    """管理端查询参数非法。"""

    def __init__(self, detail: str):
        super().__init__(detail, status_code=400)


class AdminResourceNotFoundError(AdminQueryError):
    """管理端查询资源不存在。"""

    def __init__(self, detail: str):
        super().__init__(detail, status_code=404)
