"""Reason Library 业务错误码 + 异常 + 响应工具。

约束 (T01 / T04-T09):
- 业务错误码 4xxxx (4xxx = 业务, 5xxx = 系统), 沿用项目自定义码体系
- 响应信封 {code: number, data: T | null, message: string}
- 错误时 raise BizException(exc_cls.code, exc_cls.message, status_code)
  → DRF exception_handler 转换 → ApiResponse.error()
"""
from __future__ import annotations

from typing import Any, Optional

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class BizCode:
    """业务错误码常量 (4xxx 业务, 5xxx 系统)。"""

    # === 通用 ===
    SUCCESS = 0
    VALIDATION_FAILED = 40000
    PERMISSION_DENIED = 40300
    NOT_FOUND = 40400
    CONFLICT = 40900
    INTERNAL_ERROR = 50000

    # === Tag (T04 / T10) ===
    TAG_NAME_DUPLICATED = 40001       # 同名标签 (含软删, Q-A4)
    TAG_NOT_FOUND = 40401
    SYSTEM_TAG_IMMUTABLE = 40301      # 系统预置标签不可改/停用/删
    TAG_HAS_REFS = 40901              # 标签被规则引用, 不可删
    TAG_ALREADY_ASSIGNED = 40902      # 标签已归属其它分类, 不可跨分类重复 (Item4)
    CSV_FORMAT_INVALID = 40002        # CSV 解析失败

    # === Rule (T05 / T11) ===
    RULE_NAME_DUPLICATED = 40010
    RULE_NOT_FOUND = 40410
    OPTIMISTIC_LOCK_FAILED = 41200    # PATCH / wizard save If-Match 不匹配
    SYSTEM_RULE_IMMUTABLE = 40310     # 系统预置规则不可删
    RULE_HAS_SCENE_REFS = 40910       # 规则被场景引用, 不可停用
    JSON_FORMAT_INVALID = 40011       # JSON 导入格式非法

    # === Scene (T07 / T12) ===
    RULE_SCENE_CONFLICT = 40920       # 场景已被其他规则占用

    # === Wizard (T06 / T12) ===
    CATEGORY_LEVEL_EXCEED = 40030     # 分类层级超过 4


class BizException(Exception):
    """业务异常基类 - 抛到 DRF 后被 reason_library_exception_handler 转 4xx。"""

    def __init__(
        self,
        code: int,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        extra: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}
        super().__init__(message)


# ---------------------------------------------------------------------------
# 响应工具: 统一信封 {code, data, message}
# ---------------------------------------------------------------------------

class ApiResponse:
    """统一响应信封构造器。

    用法:
        return ApiResponse.ok(data)                       # 200
        return ApiResponse.created(data)                  # 201
        return ApiResponse.error(BizCode.TAG_NAME_DUPLICATED, '...')
    """

    @staticmethod
    def ok(data: Any = None, message: str = 'OK', status_code: int = status.HTTP_200_OK) -> Response:
        return Response(
            {'code': BizCode.SUCCESS, 'data': data, 'message': message},
            status=status_code,
        )

    @staticmethod
    def created(data: Any = None, message: str = 'Created') -> Response:
        return ApiResponse.ok(data, message, status.HTTP_201_CREATED)

    @staticmethod
    def error(code: int, message: str, status_code: int = status.HTTP_400_BAD_REQUEST,
              extra: Optional[dict] = None) -> Response:
        return Response(
            {
                'code': code,
                'data': None,
                'message': message,
                **({'extra': extra} if extra else {}),
            },
            status=status_code,
        )


def reason_library_exception_handler(exc, context):
    """reason_library 自己的异常处理器。

    只处理本 app 内抛的 BizException; 其它异常走全局 apps.common 的 handler。
    注册方式: settings.REST_FRAMEWORK['EXCEPTION_HANDLER'] 不能直接换 (会破坏其他 app),
    所以在每个 view 内部显式 try/except BizException 转 ApiResponse.error().
    详见 views/__init__.py 的 _api() 装饰器。
    """
    if isinstance(exc, BizException):
        return ApiResponse.error(exc.code, exc.message, exc.status_code, exc.extra)
    return drf_exception_handler(exc, context)
