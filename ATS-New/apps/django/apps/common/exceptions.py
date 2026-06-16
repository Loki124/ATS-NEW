"""自定义异常处理"""
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


class PermissionDenied(ATSException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'permission_denied'
    default_message = '权限不足'


class NotFound(ATSException):
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


def custom_exception_handler(exc, context):
    """统一异常处理入口"""
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
        return Response(
            {
                'success': False,
                'code': getattr(exc, 'default_code', 'error'),
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
