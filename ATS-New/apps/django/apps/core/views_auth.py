"""Auth 视图 - 登录/登出/刷新"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission as AuthPermission


@api_view(['POST'])
@permission_classes([AllowAny])
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
            'permissions': list(
                AuthPermission.objects.filter(
                    ats_user_permissions__id=user.id,
                ).values_list('codename', flat=True).distinct()
            ),
        },
    })
