"""Auth 视图 - 登录/登出/刷新"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission as AuthPermission
from .models import Permission
# T01.2 (2026-08-04 寇豆码): 显式声明 IsAuthenticated, 覆盖全局 deny-by-default.
from .permissions import IsAuthenticated


class LoginRateThrottle(AnonRateThrottle):
    """Fix 6: 登录端点限速 5 次/分钟/IP, 防爆破."""
    scope = 'login'


class RegisterRateThrottle(AnonRateThrottle):
    """2026-07-02: 注册端点限速 3 次/小时/IP, 防撞库和 spam account."""
    scope = 'register'


class ChangePasswordRateThrottle(UserRateThrottle):
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
@permission_classes([IsAuthenticated])
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ChangePasswordRateThrottle])
def change_password_view(request):
    """更改当前用户密码"""
    user = request.user
    old_password = request.data.get('oldPassword') or request.data.get('old_password')
    new_password = request.data.get('newPassword') or request.data.get('new_password')

    if not old_password or not new_password:
        return Response(
            {'success': False, 'code': 'missing_password', 'message': '原密码和新密码必填'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(new_password) < 6:
        return Response(
            {'success': False, 'code': 'password_too_short', 'message': '新密码长度不能少于 6 位'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not user.check_password(old_password):
        return Response(
            {'success': False, 'code': 'invalid_old_password', 'message': '原密码错误'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save(update_fields=['password'])
    return Response({'success': True, 'message': '密码修改成功'})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """当前用户信息 - V2 权限 + 数据范围.

    GET  : 返回用户资料 + 偏好（uiSettings）。
    PATCH: 仅更新 uiSettings（合并写入 JSON，不覆盖整段），返回更新后的 me。
    """
    from django.db.utils import OperationalError, ProgrammingError
    from apps.core.models_permission_v2 import (
        PermissionResource, RolePermissionV2, UserRoleV2,
    )
    from apps.core.scope_resolver import resolve_scope
    from apps.core.models import UserPreference

    user = request.user

    # ===== PATCH: 更新 UI 偏好 =====
    if request.method == 'PATCH':
        payload = request.data or {}
        # 入参经 camel-case parser 转 snake，兼容两种 key
        ui_settings = payload.get('ui_settings')
        if ui_settings is None:
            ui_settings = payload.get('uiSettings')
        if not isinstance(ui_settings, dict):
            return Response(
                {'success': False, 'message': 'uiSettings 必须是对象'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pref = UserPreference.get_for_user(user)
        merged = {**(pref.settings or {}), **ui_settings}
        # 校验 menu_layout 合法值
        if 'menu_layout' in merged and merged['menu_layout'] not in ('side', 'top'):
            merged['menu_layout'] = 'side'
        pref.settings = merged
        pref.save(update_fields=['settings'])
        return Response({
            'success': True,
            'data': {'uiSettings': pref.settings},
        })

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
            # R8 (2026-08-03): DEPT / DEPT_AND_SUB 范围走 department_ids
            'department_ids': scope.get('department_ids', []),
            'data_scope': scope,
            # 用户 UI 偏好（菜单布局等），跟随账号
            'uiSettings': UserPreference.get_for_user(user).settings,
        },
    })
