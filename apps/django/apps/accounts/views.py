"""邮箱验证码免密登录视图。

2026-10-18 兵哥：移除自助注册后，本模块由「注册审核」改为「邮箱验证码登录」。
流程：
  1) POST /auth/email-login/send-code  输入邮箱 → 先校验账号有效性（存在 + 未停用）
     → 发验证码。待激活(PENDING)与已激活(ACTIVE)放行；不存在/已停用明确拒绝。
  2) POST /auth/email-login/verify     输入邮箱 + 验证码 → 校验通过后签发 JWT；
     若账号为 PENDING（待激活），**自动激活**为 ACTIVE。
"""
import logging

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.role_v2_query import is_super_admin
from apps.core.views_auth import EmailCodeRateThrottle, LoginRateThrottle

from . import services
from .serializers import EmailLoginSerializer, SendLoginCodeSerializer

logger = logging.getLogger(__name__)


def _find_user_by_email(email: str):
    """按邮箱定位未删除用户。username 与 email 都可能承载登录名，两者都试。"""
    from django.db.models import Q

    from apps.core.models import User
    return User.objects.filter(deleted_at__isnull=True).filter(
        Q(email__iexact=email) | Q(username__iexact=email),
    ).first()


def _issue_login_token(user):
    """签发 access/refresh 并组装 login_view 同构的返回体（含 roles + 超管兜底）。"""
    from django.db.utils import OperationalError, ProgrammingError

    from apps.core.jwt_tokens import MyRefreshToken
    from apps.core.models_permission_v2 import UserRoleV2

    refresh = MyRefreshToken.for_user(user)
    try:
        roles = list(UserRoleV2.objects.filter(
            user_id=user.id, system_code='recruit',
        ).values_list('role_code', flat=True))
    except (OperationalError, ProgrammingError):
        roles = []
    if is_super_admin(user) and 'SUPER_ADMIN' not in roles:
        roles = ['SUPER_ADMIN', *roles]
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'employee_id': user.employee_id,
            'department': user.department_id,
            'roles': roles,
        },
    }


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([EmailCodeRateThrottle])
def send_login_code_view(request):
    """发送邮箱登录验证码。发码前先校验账号有效性。"""
    serializer = SendLoginCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email'].strip().lower()

    user = _find_user_by_email(email)
    if user is None:
        return Response(
            {'success': False, 'code': 'account_not_found', 'message': '该邮箱未注册，请联系管理员开通账号'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if user.activation_status == 'DISABLED':
        return Response(
            {'success': False, 'code': 'account_disabled', 'message': '账号已停用，请联系管理员'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        services.issue_code(user.email or email, user.full_name)
    except Exception as e:  # noqa: BLE001 — 发信失败返 500（前端可重试），状态明确
        logger.error('登录验证码发送失败 email=%s err=%s', email, e, exc_info=True)
        return Response(
            {'success': False, 'code': 'SEND_FAILED', 'message': '验证码发送失败，请稍后重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return Response({
        'success': True,
        'message': '验证码已发送至您的邮箱',
        'data': {'email': user.email or email},
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def email_login_view(request):
    """邮箱验证码免密登录。校验通过后签发 JWT；PENDING 账号自动激活。"""
    serializer = EmailLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email'].strip().lower()
    code = serializer.validated_data['code']

    user = _find_user_by_email(email)
    if user is None:
        return Response(
            {'success': False, 'code': 'account_not_found', 'message': '该邮箱未注册，请联系管理员开通账号'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if user.activation_status == 'DISABLED':
        return Response(
            {'success': False, 'code': 'account_disabled', 'message': '账号已停用，请联系管理员'},
            status=status.HTTP_403_FORBIDDEN,
        )

    ok, reason = services.verify_code(user.email or email, code)
    if not ok:
        code_map = {
            'NO_CODE': '请先获取验证码',
            'EXPIRED': '验证码已过期，请重新获取',
            'LOCKED': '验证码错误次数过多，已锁定，请重新获取',
            'WRONG': '验证码不正确',
        }
        return Response(
            {'success': False, 'code': reason, 'message': code_map.get(reason, '验证失败')},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 校验通过：待激活账号自动激活（首次邮箱验证登录即激活）
    if user.activation_status == 'PENDING':
        user.set_activation_status('ACTIVE')
        user.save(update_fields=['activation_status', 'is_active', 'updated_at'])
        logger.info('账号 %s 首次邮箱验证登录，已自动激活', user.id)

    return Response({'success': True, 'data': _issue_login_token(user)})
