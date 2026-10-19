"""Auth 视图 - 登录/登出/刷新"""
import logging

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .jwt_tokens import MyRefreshToken

logger = logging.getLogger(__name__)
# T01.2 (2026-08-04 寇豆码): 显式声明 IsAuthenticated, 覆盖全局 deny-by-default.
from .permissions import IsAuthenticated
from .role_v2_query import is_super_admin


class LoginRateThrottle(AnonRateThrottle):
    """Fix 6: 登录端点限速 5 次/分钟/IP, 防爆破."""
    scope = 'login'


class EmailCodeRateThrottle(AnonRateThrottle):
    """2026-10-18 兵哥: 邮箱验证码发码限速 5 次/小时/IP, 防邮件轰炸.

    原 RegisterRateThrottle(scope='register', 3/hour) 随自助注册下线而移除，
    同一「外部触发发信」语义改由本类承担。
    """
    scope = 'email_code'


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

    # 支持多种登录方式（单一查询定位，避免 4 次串行 ORM + check_password 的 N+1）
    from django.db.models import Q

    from .models import User

    candidate_user = User.objects.filter(deleted_at__isnull=True).filter(
        Q(username=username) | Q(employee_id=username) | Q(email=username) | Q(phone=username),
    ).first()

    # 统一 401：账号不存在 / 密码错误 / 未激活但密码错误，均返回相同通用错误，
    # 消除"账号存在性枚举"信号（攻击者无密码时无法借 403/401 区分账号是否存在）。
    if candidate_user is None or not candidate_user.check_password(password):
        return Response(
            {'success': False, 'code': 'invalid_credentials', 'message': '用户名或密码错误'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # 密码正确后再告知账号状态：仅合法用户（掌握密码者）可见，不泄露账号存在性。
    # 2026-10-18 兵哥：用户状态改为三态（PENDING 待激活 / ACTIVE 已激活 / DISABLED 已停用）。
    #   待激活账号请走「邮箱验证码登录」完成首次激活，故此处给出明确指引而非笼统拒绝。
    if candidate_user.activation_status == 'DISABLED':
        return Response(
            {'success': False, 'code': 'account_disabled',
             'message': '账号已停用，请联系管理员'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if candidate_user.activation_status == 'PENDING':
        return Response(
            {'success': False, 'code': 'account_pending',
             'message': '账号待激活，请使用邮箱验证码登录并完成激活'},
            status=status.HTTP_403_FORBIDDEN,
        )

    refresh = MyRefreshToken.for_user(candidate_user)
    from django.db.utils import OperationalError, ProgrammingError

    from apps.core.models_permission_v2 import UserRoleV2
    try:
        roles = list(UserRoleV2.objects.filter(
            user_id=candidate_user.id, system_code='recruit',
        ).values_list('role_code', flat=True))
    except (OperationalError, ProgrammingError):
        roles = []
    # 超管兜底: is_superuser 用户在 roles 表未必有 SUPER_ADMIN 行, 但语义即超管.
    # 注入 SUPER_ADMIN 让前端 router guard / usePermission 统一按 SUPER_ADMIN 放行,
    # 使环境变量预设的超级管理员拥有全部菜单/功能/数据权限 (与后端 is_super_admin 同义).
    if is_super_admin(candidate_user) and 'SUPER_ADMIN' not in roles:
        roles = ['SUPER_ADMIN', *roles]
    return Response({
        'success': True,
        'data': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': candidate_user.id,
                'username': candidate_user.username,
                'full_name': candidate_user.full_name,
                'employee_id': candidate_user.employee_id,
                'department': candidate_user.department_id,
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
    except Exception as e:  # noqa: BLE001 — JWT 登出失败返 400, 不应让前端无法清状态 (token 黑名单/验证异常都应忽略)
        logger.warning('JWT 登出失败 user=%s err=%s', getattr(request.user, 'id', 'anon'), e, exc_info=True)
        return Response(
            {'success': False, 'message': '登出失败'},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ChangePasswordRateThrottle])
def change_password_view(request):
    """更改当前用户密码"""
    from .models import User

    user = request.user
    old_password = request.data.get('oldPassword') or request.data.get('old_password')
    new_password = request.data.get('newPassword') or request.data.get('new_password')

    if not old_password or not new_password:
        return Response(
            {'success': False, 'code': 'missing_password', 'message': '原密码和新密码必填'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 强度校验: 复用 Django AUTH_PASSWORD_VALIDATORS (prod: 最少12位 + 复杂度), 不再用弱校验
    try:
        validate_password(new_password, user)
    except ValidationError as e:  # noqa: BLE001 — 显式 fail-fast: 密码不合规直接 400, 不静默放行
        return Response(
            {'success': False, 'code': 'password_too_weak', 'message': '; '.join(e.messages)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not user.check_password(old_password):
        return Response(
            {'success': False, 'code': 'invalid_old_password', 'message': '原密码错误'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save(update_fields=['password'])
    # 2026-10-09 (#19): 改密即撤销所有 outstanding refresh token (旧 token 刷新时被拒)。
    User.objects.filter(id=user.id).update(token_version=F('token_version') + 1)
    return Response({'success': True, 'message': '密码修改成功'})


class TokenRefreshViewWithVersion(TokenRefreshView):
    """2026-10-09 (#19): 刷新前校验 token_version, 改密/禁用后旧 refresh 一律拒绝。

    仅校验带 token_version 声明的新 token; 存量无该声明 (含测试 fixture) 的 token 放行,
    保证向后兼容。非法/过期 token 交 simplejwt 自身返回 401。
    """

    def post(self, request, *args, **kwargs):
        raw = request.data.get('refresh')
        if raw:
            try:
                token = MyRefreshToken(raw)
                user_id = token.get('user_id')
                claim = token.get('token_version')
                if user_id is not None and claim is not None:
                    from .models import User

                    user = User.objects.filter(id=user_id, deleted_at__isnull=True).first()
                    if user is None or user.token_version != claim:
                        return Response(
                            {'success': False, 'code': 'token_revoked',
                             'message': '登录态已失效，请重新登录'},
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
            except (InvalidToken, TokenError):
                pass  # 交给 simplejwt 自身处理非法/过期 token
        return super().post(request, *args, **kwargs)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """当前用户信息 - V2 权限 + 数据范围.

    GET  : 返回用户资料 + 偏好（uiSettings）。
    PATCH: 仅更新 uiSettings（合并写入 JSON，不覆盖整段），返回更新后的 me。
    """
    from django.db.utils import OperationalError, ProgrammingError

    from apps.core.models import UserPreference
    from apps.core.models_permission_v2 import (
        PermissionResource,
        RolePermissionV2,
        UserRoleV2,
    )
    from apps.core.scope_resolver import resolve_scope

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
        if is_super_admin(user):
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
                    # 动态策略并集: 用户被指派且启用的策略所授予的资源码并入功能权限.
                    # 任一策略授予的码 -> 并集; 未管辖的功能退回基础 role_permission (策略只授予自身码).
                    try:
                        from apps.core.models_permission_v2 import (
                            DynamicStrategy,
                            DynamicStrategyAssignment,
                        )
                        strategy_codes = list(DynamicStrategyAssignment.objects.filter(
                            role_code__in=role_codes,
                        ).values_list('strategy_code', flat=True))
                        if strategy_codes:
                            granted = DynamicStrategy.objects.filter(
                                strategy_code__in=strategy_codes, status=1,
                            ).values_list('granted_resource_codes', flat=True)
                            extra = set()
                            for codes in granted:
                                if codes:
                                    extra.update(codes)
                            if extra:
                                permissions = list(set(permissions) | extra)
                    except (OperationalError, ProgrammingError):
                        # 动态策略表尚不存在时静默跳过, 不阻断 /me
                        pass
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

    # 超管兜底: is_superuser 用户在 roles 表未必有 SUPER_ADMIN 行, 但语义即超管.
    # 注入 SUPER_ADMIN + 全量 scope, 使前端 router guard / usePermission 统一放行,
    # 且 /me.data_scope 如实反映"全量可见" —— 环境变量预设的超级管理员拥有
    # 全部菜单/功能/数据权限 (与后端 is_super_admin / scope_filter_q bypass 同义).
    if user.is_authenticated and is_super_admin(user):
        if 'SUPER_ADMIN' not in roles:
            roles = ['SUPER_ADMIN', *roles]
        scope = {'all': True}

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
