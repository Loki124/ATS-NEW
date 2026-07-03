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
                'roles': list(user.user_roles.values_list('role__code', flat=True)),
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
    """当前用户信息"""
    user = request.user
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
            'roles': list(user.user_roles.values_list('role__code', flat=True)),
            # 2026-06-17: 改为 role-derived RBAC Permission.code (e.g. 'candidate:read', 'process:write')
            # 之前用 AuthPermission (django.contrib.auth.models.Permission, codename 如 'add_candidate')
            # 与 init_demo_data 创建的 apps.core.Permission (code 'candidate:read') 是两套独立体系,
            # 对 admin 永远返回 []. 现在: SUPER_ADMIN 拿到所有 Permission.code; 其他角色拿到
            # 通过 user.user_roles → role → RolePermission → Permission 串起来的去重并集.
            #
            # 反向关系命名:
            #   Permission ← (default reverse: rolepermission) ← RolePermission
            #   Role       ← (default reverse: userrole)        ← UserRole
            # ('user_roles' 是 UserRole.user → User 的反向 related_name, 不是 Role 侧)
            'permissions': (
                list(Permission.objects.values_list('code', flat=True))
                if user.is_superuser
                else list(
                    Permission.objects
                        .filter(rolepermission__role__userrole__user=user)
                        .values_list('code', flat=True)
                        .distinct()
                )
            ),
        },
    })
