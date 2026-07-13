"""Auth 视图 - 登录/登出/刷新"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission as AuthPermission
from .models import Permission


class LoginRateThrottle(AnonRateThrottle):
    """Fix 6: 登录端点限速 5 次/分钟/IP, 防爆破."""
    scope = 'login'


class RegisterRateThrottle(AnonRateThrottle):
    """2026-07-02: 注册端点限速 3 次/小时/IP, 防撞库和 spam account."""
    scope = 'register'


class ChangePasswordRateThrottle(AnonRateThrottle):
    """2026-07-02: 改密端点限速 5 次/分钟/用户, 防被撞改密."""
    scope = 'change_password'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    """登录 - 支持 username / 工号 / 邮箱 / 手机号"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'success': False, 'code': 'missing_credentials', 'message': '用户名和密码必填'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 支持多种登录方式
    user = None
    from .models import User
    for lookup in ['username', 'employee_id', 'email', 'phone']:
        try:
            candidate = User.objects.get(**{lookup: username}, is_active=True, deleted_at__isnull=True)
            if candidate.check_password(password):
                user = candidate
                break
        except User.DoesNotExist:
            continue

    if not user:
        return Response(
            {'success': False, 'code': 'invalid_credentials', 'message': '用户名或密码错误'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(user)
    from apps.core.models_permission_v2 import UserRoleV2
    from django.db.utils import OperationalError, ProgrammingError
    try:
        roles = list(UserRoleV2.objects.filter(
            user_id=user.id, system_code='recruit',
        ).values_list('role_code', flat=True))
    except (OperationalError, ProgrammingError):
        roles = []
    return Response({
        'success': True,
        'data': {
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
        },
    })


@api_view(['POST'])
def logout_view(request):
    """登出 - 撤销 refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'success': True})
    except Exception:
        return Response(
            {'success': False, 'message': '登出失败'},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['GET'])
def me_view(request):
    """当前用户信息 - V2 权限 + 数据范围."""
    from django.db.utils import OperationalError, ProgrammingError
    from apps.core.models_permission_v2 import (
        PermissionResource, RolePermissionV2, UserRoleV2,
    )
    from apps.core.scope_resolver import resolve_scope

    user = request.user
    permissions = []
    if user.is_authenticated:
        if getattr(user, 'is_superuser', False):
            try:
                permissions = list(PermissionResource.objects.filter(
                    status=1, system_code='recruit',
                ).values_list('resource_code', flat=True))
            except (OperationalError, ProgrammingError):
                permissions = []
        else:
            try:
                role_codes = list(UserRoleV2.objects.filter(
                    user_id=user.pk,
                ).values_list('role_code', flat=True))
                if role_codes:
                    permissions = list(RolePermissionV2.objects.filter(
                        role_code__in=role_codes, system_code='recruit',
                    ).values_list('resource_code', flat=True).distinct())
            except (OperationalError, ProgrammingError):
                permissions = []

    scope = {}
    roles = []
    if user.is_authenticated:
        try:
            scope = resolve_scope(user)
        except (OperationalError, ProgrammingError):
            scope = {}
        try:
            roles = list(UserRoleV2.objects.filter(
                user_id=user.pk, system_code='recruit',
            ).values_list('role_code', flat=True))
        except (OperationalError, ProgrammingError):
            roles = []

    return Response({
        'success': True,
        'data': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'employee_id': user.employee_id,
            'email': user.email,
            'phone': user.phone,
            'department': user.department_id,
            'department_name': user.department.name if user.department else None,
            'position_title': user.position_title,
            'level': user.level,
            'roles': roles,
            'permissions': permissions,
            'management_unit_ids': scope.get('management_unit_ids', []),
            'data_scope': scope,
        },
    })
