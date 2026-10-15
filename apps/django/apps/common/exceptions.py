"""自定义异常处理

P1-7 修复: 业务异常细分,前端能精准区分处理
- 401 未登录: 应跳转登录页
- 403 无权限: 应显示"无权限"提示
- 403 对象权限: 应隐藏该资源/不显示入口
- 404 资源不存在
- 409 状态机/条件冲突
- 400 参数校验失败

2026-10-15 新增: "库没跟上代码" 的自诊断 (db_schema_out_of_sync)
  背景: 新 app 注册进 INSTALLED_APPS + 迁移文件在仓, 但本地库没跑 migrate,
  ORM 抛 ProgrammingError(1146 Table ... doesn't exist) → 这里原来一律包成
  笼统的 500 "服务器内部错误", 前端只弹"服务繁忙", 排查方向被带偏
  (实测先怀疑了代码 bug / 权限 / 迁移文件缺失, 实际只需跑 migrate)。
  现在这类错误单独识别 + 返回可执行提示, 开发期一眼定位。
"""
import logging
import re

from django.conf import settings
from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.common.response import error_response

logger = logging.getLogger(__name__)


class ATSException(Exception):
    """ATS 业务异常基类"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'ats_error'
    default_message = '业务异常'

    def __init__(self, message=None, code=None, status_code=None, extra=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        if status_code is not None:
            self.status_code = status_code
        self.extra = extra or {}
        super().__init__(self.message)


class UnauthenticatedError(ATSException):
    """P1-7: 未登录/会话过期 (401)

    与 PermissionDenied 区分:
    - UnauthenticatedError: user is anonymous → 前端应跳登录页
    - PermissionDenied: user 已登录但没权限 → 前端应显示"无权限"提示
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = 'unauthenticated'
    default_message = '请先登录'


class PermissionDenied(ATSException):
    """403 - 用户已登录但功能/数据权限不足"""
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'permission_denied'
    default_message = '权限不足'


class ObjectPermissionDenied(ATSException):
    """P1-7: 403 - 对象级权限不足（数据权限/字段级 ACL）

    与 PermissionDenied 区分:
    - PermissionDenied: 整个功能没权限（如没"删除"按钮的权限）
    - ObjectPermissionDenied: 功能有权限,但此具体对象不在授权范围内

    前端响应:
    - 列表场景: 过滤掉该对象
    - 详情场景: 显示 404 或"该资源不存在/无权访问"
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'object_permission_denied'
    default_message = '无权访问该资源'


class NotFound(ATSException):
    """404 - 资源不存在（或被软删除/不在数据权限范围内）"""
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'not_found'
    default_message = '资源不存在'


class ValidationError(ATSException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'validation_error'
    default_message = '参数校验失败'


class StateTransitionError(ATSException):
    """状态机转换错误"""
    status_code = status.HTTP_409_CONFLICT
    default_code = 'state_transition_error'
    default_message = '状态转换非法'


class EntryConditionNotMet(ATSException):
    """进入条件不满足"""
    status_code = status.HTTP_409_CONFLICT
    default_code = 'entry_condition_not_met'
    default_message = '不满足进入条件'


# === P1-7 业务异常码注册表 ===
# 前端可通过 code 字段精准识别
BUSINESS_EXCEPTION_CODES = frozenset({
    'unauthenticated',
    'permission_denied',
    'object_permission_denied',
    'not_found',
    'validation_error',
    'state_transition_error',
    'entry_condition_not_met',
})


def custom_exception_handler(exc, context):
    """统一异常处理入口

    P1-7: 增强响应 payload
    - 在 401/403/404 响应中显式标记 code
    - 前端可基于此做精细化处理(跳转/隐藏/降级)
    """
    # 业务异常
    if isinstance(exc, ATSException):
        return Response(
            {
                'success': False,
                'code': exc.code,
                'message': exc.message,
                'data': None,
                'extra': exc.extra,
            },
            status=exc.status_code,
        )

    # DRF 异常
    response = exception_handler(exc, context)
    if response is not None:
        # P1-7: 把 DRF 异常映射到我们的 code
        code = _map_drf_to_code(exc, response.status_code)
        # 限流异常保留 DRF 自带的等待时间提示，避免前端只能看到笼统的"请求处理失败"
        message = '请求处理失败'
        if code == 'throttled' and isinstance(response.data, dict):
            message = response.data.get('detail') or message
        return error_response(
            message=message,
            code=code,
            status_code=response.status_code,
            data=None,
            errors=response.data,
        )

    # 未捕获异常
    logger.exception('Unhandled exception: %s', exc)

    # 🔴 "库没跟上代码" 自诊断: 表/列不存在几乎不是代码 bug, 而是漏跑 migrate。
    #    识别出来就返回可执行提示, 别再让排查跑去怀疑代码和权限。
    hint = _db_schema_out_of_sync_hint(exc)
    if hint:
        return error_response(
            message=hint,
            code='db_schema_out_of_sync',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            data=None,
        )

    return error_response(
        message='服务器内部错误',
        code='internal_error',
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        data=None,
    )


# MySQL 1146 = 表不存在, 1054 = 列不存在。SQLite 措辞不同, 一并匹配。
_MISSING_TABLE_RE = re.compile(
    r"Table '(?P<table>[\w.]+)' doesn't exist"
    r"|no such table:\s*(?P<sqlite_table>[\w.]+)",
    re.IGNORECASE,
)
_MISSING_COLUMN_RE = re.compile(
    r"Unknown column '(?P<column>[\w.]+)' in 'field list'"
    r"|no such column:\s*(?P<sqlite_column>[\w.]+)",
    re.IGNORECASE,
)


def _db_schema_out_of_sync_hint(exc):
    """识别"迁移未跑"类 DB 错误, 返回可直接照做的提示; 非此类返回 None。

    只在 DEBUG=True 时给具体表名/迁移命令 —— 生产环境不泄漏 schema 信息,
    但仍然返回 code 让前端能区分"这是环境问题, 不是接口 bug"。
    """
    if not isinstance(exc, DatabaseError):
        return None

    msg = str(exc)

    match = _MISSING_TABLE_RE.search(msg)
    if match:
        table = match.group('table') or match.group('sqlite_table')
        detail = f'数据表 {table} 不存在' if table else '数据表不存在'
    else:
        match = _MISSING_COLUMN_RE.search(msg)
        if not match:
            return None
        column = match.group('column') or match.group('sqlite_column')
        detail = f'字段 {column} 不存在' if column else '字段不存在'

    if not settings.DEBUG:
        # 生产: 不暴露具体表名, 但标记为环境问题便于排查
        return '数据库结构与代码版本不一致，请联系管理员执行数据库迁移'

    return f'数据库结构与代码不一致（{detail}），本地开发请执行：python manage.py migrate'


def _map_drf_to_code(exc, status_code):
    """把 DRF 异常映射为我们的业务 code,方便前端统一处理"""
    if status_code == 401:
        return 'unauthenticated'
    if status_code == 403:
        # DRF 的 PermissionDenied 区分不出来"功能无权限"和"对象无权限"
        # 默认按 PermissionDenied 处理
        return 'permission_denied'
    if status_code == 404:
        return 'not_found'
    if status_code == 400:
        return 'validation_error'
    if status_code == 409:
        return 'state_transition_error'
    return getattr(exc, 'default_code', 'error')
