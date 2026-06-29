"""自定义异常处理

P1-7 修复: 业务异常细分,前端能精准区分处理
- 401 未登录: 应跳转登录页
- 403 无权限: 应显示"无权限"提示
- 403 对象权限: 应隐藏该资源/不显示入口
- 404 资源不存在
- 409 状态机/条件冲突
- 400 参数校验失败
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

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
                'extra': exc.extra,
            },
            status=exc.status_code,
        )

    # DRF 异常
    response = exception_handler(exc, context)
    if response is not None:
        # P1-7: 把 DRF 异常映射到我们的 code
        code = _map_drf_to_code(exc, response.status_code)
        return Response(
            {
                'success': False,
                'code': code,
                'message': '请求处理失败',
                'errors': response.data,
            },
            status=response.status_code,
        )

    # 未捕获异常
    logger.exception('Unhandled exception: %s', exc)
    return Response(
        {
            'success': False,
            'code': 'internal_error',
            'message': '服务器内部错误',
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


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
