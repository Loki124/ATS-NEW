"""FE 期望的 stub endpoint 兜底 (2026-07-01)

合并第一批 (auth/candidate batch/recruitment-process/offer-template/scoring/upload-parse)
+ 第二批 (permissions/permissions-v2/talent-pool/resumes 等).

所有 endpoint 一律返合理 stub 避免 404:
  - GET 返空 list / 空 data
  - POST 返 {success: true, data: {id: 'stub-uuid'}}
  - PUT/PATCH 返 echo

2026-08-03 警告机制 (产品经理跑通):
  - 每次 stub 调用: 1) response 加 X-Stub: true header 2) WARNING log 记录
  - 监控/审计: 生产环境日志聚合 (ELK / Sentry) 检测到 'stub endpoint called' 应该立即跟进
  - 真要补实现: 把 view 改到对应 app 的 views.py, 在 urls.py 删 stub import

2026-08-03 R5/R6 (寇豆码) 安全收敛:
  - **安全敏感的 stub 一律不许假成功**。auth/register 与 auth/change-password
    原本返 200 success:true 却一行库都不写, 用户以为注册成功 / 密码已改, 实际没有。
    现在统一走 _not_implemented() 返 501 + success:false + X-Stub:true + ERROR 日志。
  - /login 别名补上 LoginRateThrottle, 与 /auth/login 共用 'login' scope,
    否则换个 URL 就能绕开撞库限流。
  - 只读类 stub (返空 list) 保持原样, 它们不会误导用户以为写入成功。
"""
import logging
import uuid
from django.urls import path
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from apps.core.permissions import ResourceScoped, IsAuthenticatedReadOnly
from apps.core.views_auth import (
    LoginRateThrottle,
    RegisterRateThrottle,
    ChangePasswordRateThrottle,
)

logger = logging.getLogger('apps.stub')


# T01.2 (2026-08-04 寇豆码): 默认 deny-by-default 落地后, 所有 stub 必须显式声明
# permission_classes. 这里给两个常用 mode 写工厂函数, 替代原本裸 @permission_classes([IsAuthenticated]).
#
# - scoped_view  → 业务端点, [ResourceScoped] + resource_code
# - readonly_view → 纯读列表 stub, [IsAuthenticatedReadOnly] + resource_code
# - public_view → 真正公开 (rare, 当前没用上)
def _scoped_view(methods, resource_code):
    """包装业务 stub: ResourceScoped + resource_code.
    ResourceScoped 走 apps.core.scope_resolver.resolve_scope 4 层堆栈, superuser bypass.
    """
    def deco(func):
        wrapped = api_view(methods)(permission_classes([ResourceScoped])(func))
        wrapped.cls.resource_code = resource_code
        wrapped.cls.__name__ = func.__name__
        return wrapped
    return deco


def _readonly_view(methods, resource_code):
    """包装只读 stub: IsAuthenticatedReadOnly + resource_code.
    GET → 仅需登录; 写方法必须 view 同时声明 [ResourceScoped] 才能放行.
    """
    def deco(func):
        wrapped = api_view(methods)(permission_classes([IsAuthenticatedReadOnly])(func))
        wrapped.cls.resource_code = resource_code
        wrapped.cls.__name__ = func.__name__
        return wrapped
    return deco


def _ok(data=None, code=200):
    """构造 stub 响应 + 标记 X-Stub header + 日志告警."""
    response = Response({'success': True, 'data': data}, status=code)
    response['X-Stub'] = 'true'
    return response


def _empty_list():
    response = Response({'success': True, 'data': [], 'pagination': {'page': 1, 'pageSize': 20, 'total': 0, 'totalPages': 1, 'hasNext': False, 'hasPrevious': False}})
    response['X-Stub'] = 'true'
    return response


def _log_stub_hit(view_name: str, request):
    """记录 stub 被调用, 方便监控告警 + 后续补实现."""
    logger.warning(
        'STUB endpoint called: view=%s method=%s path=%s user=%s ip=%s — 请到 apps/referral/urls_stubs.py 补真实现',
        view_name,
        request.method,
        request.path,
        getattr(request.user, 'id', 'anon'),
        request.META.get('REMOTE_ADDR', 'unknown'),
    )


def _not_implemented(view_name: str, request, message: str, code: int = 501,
                     error_code: str = 'not_implemented'):
    """2026-08-03 R5/R6 (寇豆码): 安全敏感 stub 一律返明确错误, 绝不假装成功.

    背景 (docs/ARCHITECTURE_REVIEW_2026-08-03.md):
      原 auth_register / auth_change_password 直接 `_ok(...)` 返 200 + success:true,
      但**一行库都没写**。前端拿到 200 就提示"注册成功 / 密码已更新",
      用户以为改了密码,实际旧密码依然有效 —— 这是安全事故级别的假成功。

    统一约定:
      - HTTP 501 Not Implemented (功能尚未实现) 或 403 (明确拒绝)
      - body: {success: false, code, message, stub: true}
      - 保留 X-Stub: true 响应头, 便于网关/前端识别
      - 日志级别提到 ERROR (不是 WARNING), 生产日志聚合必须能告警
    """
    logger.error(
        'STUB endpoint REFUSED (未实现, 已返回 %s): view=%s method=%s path=%s user=%s ip=%s',
        code,
        view_name,
        request.method,
        request.path,
        getattr(request.user, 'id', 'anon'),
        request.META.get('REMOTE_ADDR', 'unknown'),
    )
    response = Response(
        {
            'success': False,
            'code': error_code,
            'message': message,
            'stub': True,
        },
        status=code,
    )
    response['X-Stub'] = 'true'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticatedReadOnly])
def _empty_list_view(request):
    _log_stub_hit('_empty_list_view', request)
    return _empty_list()


# 多 URL 复用同一 view, resource_code 按 URL 注入 (route 注册时覆盖).
_empty_list_view.cls.resource_code = 'recruit:candidate:list'


# ============================================================
# Auth
# ============================================================
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterRateThrottle])
def auth_register(request):
    """POST /auth/register — 尚未实现.

    R5 (2026-08-03): 原实现返 200 + {id: 'user-stub-xxxx', status: 'ACTIVE'},
    前端据此提示"注册成功",但数据库里根本没有这个用户,下一步登录必然失败。
    现在明确返 501,由前端展示"该功能尚未开放"。
    """
    return _not_implemented(
        'auth_register',
        request,
        '用户自助注册功能尚未实现。请联系管理员在「用户管理」中创建账号。',
        code=501,
    )


# DEPRECATED stub (T03 删): 留 IsAuthenticated 是为了让 FE 拿到 501 而不是 403.
# 全局默认 deny-by-default 后, 这里显式声明 IsAuthenticated 放行登录用户, 由 view 体返回 501.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ChangePasswordRateThrottle])
def auth_change_password(request):
    """POST /auth/change-password — 尚未实现.

    R6 (2026-08-03): 原实现返 200 + {'message': '密码已更新 (stub)'},
    但**没有任何写库动作**。用户以为密码已改、旧密码已失效,实际旧密码仍可登录 ——
    典型的安全假成功。现在明确返 501。
    """
    return _not_implemented(
        'auth_change_password',
        request,
        '修改密码功能尚未实现，你的密码没有被更改。请联系管理员重置密码。',
        code=501,
    )


# ============================================================
# Login alias (单数) — POST /login
# ============================================================
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_alias(request):
    """POST /login — /auth/login 的单数别名, 走真实认证.

    R6 (2026-08-03): 原来这个 alias **没有任何限流**, 而 apps/core/views_auth.py:31
    的正式登录入口挂了 LoginRateThrottle(scope='login')。攻击者只要把 URL 从
    /auth/login 换成 /login 就能无限次撞库。这里补上同一个 throttle class,
    与正式入口共用 'login' scope, 配额也就共享。
    """
    from django.contrib.auth import authenticate
    from rest_framework_simplejwt.tokens import RefreshToken
    user = authenticate(username=request.data.get('username', ''), password=request.data.get('password', ''))
    if user is None:
        logger.warning(
            'login_alias 认证失败: username=%s ip=%s',
            request.data.get('username', ''),
            request.META.get('REMOTE_ADDR', 'unknown'),
        )
        return Response({'success': False, 'code': 'invalid_credentials', 'message': '用户名或密码错误'}, status=401)
    refresh = RefreshToken.for_user(user)
    return Response({
        'success': True,
        'data': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {'id': user.id, 'username': user.username, 'isStaff': user.is_staff}
        }
    })


# ============================================================
# Candidate batch (G9 PRD)
# ============================================================
@_scoped_view(methods=['POST'], resource_code='recruit:candidate:create')
def candidate_batch_recommend(request):
    _log_stub_hit('candidate_batch_recommend', request)
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True, 'recommendationId': f'rec-stub-{uuid.uuid4().hex[:8]}'} for cid in ids]})


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:edit')
def candidate_batch_archive(request):
    _log_stub_hit('candidate_batch_archive', request)
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True} for cid in ids]})


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:edit')
def candidate_batch_assign(request):
    _log_stub_hit('candidate_batch_assign', request)
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True, 'recruiterId': request.data.get('recruiterId')} for cid in ids]})


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:export')
def candidate_batch_export(request):
    _log_stub_hit('candidate_batch_export', request)
    return _ok({'jobId': f'export-stub-{uuid.uuid4().hex[:8]}', 'status': 'PENDING'})


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:edit')
def candidate_batch_screen(request):
    _log_stub_hit('candidate_batch_screen', request)
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True, 'result': request.data.get('result', 'PASS')} for cid in ids]})


# ============================================================
# Recruitment process (G38)
# ============================================================
@_scoped_view(methods=['GET', 'POST'], resource_code='recruit:role:list')
def stage_rules(request):
    _log_stub_hit('stage_rules', request)
    if request.method == 'GET':
        return _empty_list()
    return _ok({'id': f'sr-stub-{uuid.uuid4().hex[:8]}', **request.data})


@_scoped_view(methods=['GET', 'POST'], resource_code='recruit:role:list')
def auto_archive_rules(request):
    _log_stub_hit('auto_archive_rules', request)
    if request.method == 'GET':
        return _empty_list()
    return _ok({'id': f'aar-stub-{uuid.uuid4().hex[:8]}', **request.data})


@_scoped_view(methods=['GET'], resource_code='recruit:candidate:list')
def evaluate_candidate(request, candidate_id):
    _log_stub_hit('evaluate_candidate', request)
    return _ok({'passed': True, 'failedItems': [], 'prompt': None, 'candidateId': candidate_id})


@_scoped_view(methods=['GET'], resource_code='recruit:application:list')
def check_stage_transition(request, application_id):
    _log_stub_hit('check_stage_transition', request)
    return _ok({'canTransition': True, 'nextStageId': None, 'applicationId': application_id, 'checks': []})


@_scoped_view(methods=['GET'], resource_code='recruit:application:list')
def check_stage_transition_no_id(request):
    _log_stub_hit('check_stage_transition_no_id', request)
    return _ok({'canTransition': True, 'nextStageId': None, 'applicationId': None, 'checks': []})


@_scoped_view(methods=['GET'], resource_code='recruit:application:list')
def check_stage_transition_top(request):
    _log_stub_hit('check_stage_transition_top', request)
    return _ok({'canTransition': True, 'nextStageId': None, 'applicationId': None, 'checks': []})


@_scoped_view(methods=['GET', 'POST', 'PUT'], resource_code='recruit:application:list')
def recruitment_rounds(request, id=None):
    _log_stub_hit('recruitment_rounds', request)
    if request.method == 'GET':
        return _empty_list()
    if request.method == 'POST':
        return _ok({'id': f'rr-stub-{uuid.uuid4().hex[:8]}', **request.data})
    return _ok({'id': id, 'status': request.data.get('status', 'ACTIVE')})


@_scoped_view(methods=['PUT'], resource_code='recruit:application:advance')
def recruitment_rounds_status(request, id):
    _log_stub_hit('recruitment_rounds_status', request)
    return _ok({'id': id, 'status': request.data.get('status', 'ACTIVE')})


# ============================================================
# Add candidate: bulk-create, upload-and-parse, scoring
# ============================================================
@_scoped_view(methods=['POST'], resource_code='recruit:candidate:create')
def bulk_create(request):
    _log_stub_hit('bulk_create', request)
    candidates = request.data.get('candidates', [])
    return _ok({'results': [{'success': True, 'id': f'c-stub-{uuid.uuid4().hex[:8]}'} for _ in candidates]})


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:create')
def upload_and_parse(request):
    _log_stub_hit('upload_and_parse', request)
    return _ok({'jobId': f'parse-stub-{uuid.uuid4().hex[:8]}', 'status': 'PENDING', 'fileCount': len(request.FILES)})


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:create')
def scoring_start(request):
    _log_stub_hit('scoring_start', request)
    return _ok({'jobId': f'score-stub-{uuid.uuid4().hex[:8]}', 'status': 'PENDING'})


# ============================================================
# Offer templates
# ============================================================
@_scoped_view(methods=['GET', 'POST'], resource_code='recruit:offer:list')
def offer_templates(request):
    _log_stub_hit('offer_templates', request)
    if request.method == 'GET':
        return _empty_list()
    return _ok({'id': f'ot-stub-{uuid.uuid4().hex[:8]}', **request.data})


@_scoped_view(methods=['POST'], resource_code='recruit:offer:edit')
def offer_template_render(request):
    _log_stub_hit('offer_template_render', request)
    return _ok({'fileUrl': f'https://stub.example.com/render-{uuid.uuid4().hex[:8]}.pdf', 'format': request.data.get('format', 'pdf')})


# ============================================================
# Global search + Evaluate
# ============================================================
@_readonly_view(methods=['GET'], resource_code='recruit:candidate:list')
def global_search(request):
    _log_stub_hit('global_search', request)
    return _ok({'candidates': [], 'positions': [], 'demands': [], 'invitations': [], 'total': 0, 'query': request.query_params.get('q', '')})


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:list')
def evaluate(request):
    _log_stub_hit('evaluate', request)
    return _ok({'score': 0, 'passed': False, 'details': []})


# ============================================================
# Permissions v1 (FE 期望 /permissions/* 走这里)
# 2026-07-01: 已有 Role/Permission model, 这些是 alias 调真 endpoint
# ============================================================
@_scoped_view(methods=['GET'], resource_code='recruit:role:list')
def permissions_roles_list(request):
    _log_stub_hit('permissions_roles_list', request)
    """GET /permissions/roles/ — 角色列表 (alias 调 /roles/)

    T30.175: V1 Role 表已 DROP, 改读 RoleV2 (兼容字段 code/name/is_active/...).
    """
    from apps.core.models_permission_v2 import RoleV2
    from apps.core.serializers import RoleSerializer
    qs = RoleV2.objects.filter(status=1)
    search = request.query_params.get('search', '')
    if search:
        qs = qs.filter(role_name__icontains=search) | qs.filter(role_code__icontains=search)
    data = RoleSerializer(qs[:50], many=True).data
    return Response({'success': True, 'data': data})


@_scoped_view(methods=['GET'], resource_code='recruit:user_role:list')
def permissions_user_roles(request, user_id):
    _log_stub_hit('permissions_user_roles', request)
    """GET /permissions/users/{id}/roles — 用户的角色

    T30.175: V1 UserRole 表已 DROP, 改读 UserRoleV2 (role_code) + RoleV2.
    """
    from apps.core.models_permission_v2 import UserRoleV2, RoleV2
    role_codes = list(UserRoleV2.objects.filter(
        user_id=user_id, system_code='recruit',
    ).values_list('role_code', flat=True).distinct())
    roles = RoleV2.objects.filter(role_code__in=role_codes, status=1)
    from apps.core.serializers import RoleSerializer
    data = RoleSerializer(roles, many=True).data
    return Response({'success': True, 'data': data})


@_scoped_view(methods=['GET'], resource_code='recruit:role:list')
def permissions_user_info(request):
    _log_stub_hit('permissions_user_info', request)
    """GET /permissions/user-info/ — 当前用户权限 + 角色

    T30.175: V1 UserRole 表已 DROP, 改读 UserRoleV2 + RoleV2.
    """
    from apps.core.models_permission_v2 import UserRoleV2, RoleV2
    user = request.user
    role_codes = list(UserRoleV2.objects.filter(
        user_id=user.id, system_code='recruit',
    ).values_list('role_code', flat=True).distinct())
    roles = RoleV2.objects.filter(role_code__in=role_codes, status=1)
    from apps.core.serializers import RoleSerializer
    return Response({
        'success': True,
        'data': {
            'userId': str(user.id),
            'username': user.username,
            'isStaff': user.is_staff,
            'isSuperuser': user.is_superuser,
            'roles': RoleSerializer(roles, many=True).data,
            'permissions': list(user.get_all_permissions()) if hasattr(user, 'get_all_permissions') else [],
        }
    })


@_scoped_view(methods=['GET'], resource_code='recruit:mou:list')
def permissions_mous_list(request):
    _log_stub_hit('permissions_mous_list', request)
    """GET /permissions/mous/ — MOU 列表 (FE UserManagement.vue 分配MOU 弹窗用)

    2026-07-02: 实调 MouAgreement, 序列化成 FE 期望 {id, name, code, type, description}.
    MouAgreement model 字段 id/code/company_name/mou_type/terms, to_representation 已加 name/description/mouType 别名.
    """
    from apps.mou.models import MouAgreement
    from apps.mou.serializers import MouAgreementSerializer
    qs = MouAgreement.objects.filter(status='ACTIVE').order_by('code')[:200]
    serializer = MouAgreementSerializer(qs, many=True)
    data = []
    for mou in serializer.data:
        data.append({
            'id': mou.get('id'),
            'name': mou.get('name') or mou.get('code'),
            'code': mou.get('code'),
            'type': mou.get('mouType') or 'STANDARD',
            'description': mou.get('description') or '',
        })
    return Response({'success': True, 'data': data})


@_scoped_view(methods=['GET', 'POST'], resource_code='recruit:user_role:edit')
def permissions_user_mous(request, user_id):
    _log_stub_hit('permissions_user_mous', request)
    """GET /permissions/user-mous/{user_id} — 用户已分配的 MOU 列表 (mouId 列表)
    POST /permissions/user-mous/{user_id} body {mouIds: []} — 覆盖式保存用户的 MOU 分配.

    2026-07-02: User model 无 mou M2M 字段, 暂存 UserRole.department 字段 (复用 placeholder).
    真实 G36+ 实现会引入 UserMOU M2M 表; 现在返空 list + echo 保存即可, 让 FE 弹窗能正常工作.
    """
    if request.method == 'GET':
        # 真有 MOU 表的话, 这里会查 UserMOU 表; 现在返 []
        return Response({'success': True, 'data': []})
    # POST: echo save, 真写库逻辑待 UserMOU 表
    mou_ids = request.data.get('mouIds', [])
    if not isinstance(mou_ids, list):
        return Response({'success': False, 'code': 'validation_error', 'message': 'mouIds 必须是 list'}, status=400)
    return Response({'success': True, 'data': {'userId': str(user_id), 'mouIds': mou_ids}})


@_scoped_view(methods=['GET'], resource_code='recruit:role:list')
def permissions_list_by_type(request):
    _log_stub_hit('permissions_list_by_type', request)
    """GET /permissions/permissions/list?type=MENU|FUNCTION|DATA — 权限字典
    2026-07-13 (T30.175 follow-up): 切换到 V2 PermissionResource (V1 permissions 表已在 T17 DROP).
    V2 用 `resource_type` (MENU/BUTTON/API) 区分菜单 vs 功能. 数据权限 (DATA) 用 config_key 占位.
    """
    from apps.core.models_permission_v2 import PermissionResource
    qs = PermissionResource.objects.filter(status=1, system_code='recruit')
    type_filter = request.query_params.get('type', '')
    if type_filter == 'MENU':
        qs = qs.filter(resource_type='MENU')
    elif type_filter == 'FUNCTION':
        qs = qs.filter(resource_type='BUTTON')
    elif type_filter == 'DATA':
        # 数据权限字典: 暂返 1 行占位, V2 数据范围配置待 G37+ 实现
        return Response({'success': True, 'data': [{
            'id': 'system:admin',
            'code': 'system:admin',
            'name': '全公司数据',
            'type': 'DATA',
            'resourceType': 'DATA',
        }]})
    elif type_filter == 'API':
        qs = qs.filter(resource_type='API')
    rows = qs.order_by('module', 'sort_order', 'id')[:200].values(
        'id', 'resource_code', 'resource_name', 'resource_type', 'module', 'parent_code',
        'sort_order',
    )
    data = [
        {
            'id': r['resource_code'],
            'code': r['resource_code'],
            'name': r['resource_name'],
            'type': r['resource_type'],
            'resourceType': r['resource_type'],
            'module': r['module'],
            'parentCode': r['parent_code'],
        }
        for r in rows
    ]
    return Response({'success': True, 'data': data})


@_scoped_view(methods=['GET'], resource_code='recruit:role:list')
def permissions_functions(request):
    _log_stub_hit('permissions_functions', request)
    """GET /permissions/functions/ — 功能权限 (BUTTON 操作).  V2 切到 PermissionResource."""
    from apps.core.models_permission_v2 import PermissionResource
    qs = PermissionResource.objects.filter(
        status=1, system_code='recruit', resource_type='BUTTON',
    ).order_by('module', 'sort_order', 'id')[:200]
    data = [
        {
            'id': r.resource_code,
            'code': r.resource_code,
            'name': r.resource_name,
            'type': r.resource_type,
            'resourceType': r.resource_type,
            'module': r.module,
        }
        for r in qs
    ]
    return Response({'success': True, 'data': data})


@_scoped_view(methods=['GET'], resource_code='recruit:role:menu:view')
def permissions_menus(request):
    _log_stub_hit('permissions_menus', request)
    """GET /permissions/menus/ — 菜单/读权限.  V2 切到 PermissionResource (resource_type=MENU)."""
    from apps.core.models_permission_v2 import PermissionResource
    qs = PermissionResource.objects.filter(
        status=1, system_code='recruit', resource_type='MENU',
    ).order_by('module', 'sort_order', 'id')[:200]
    data = [
        {
            'id': r.resource_code,
            'code': r.resource_code,
            'name': r.resource_name,
            'type': r.resource_type,
            'resourceType': r.resource_type,
            'module': r.module,
        }
        for r in qs
    ]
    return Response({'success': True, 'data': data})


# ============================================================
# 2026-07-01 花无缺: permissions-v2/* 5 个 stub view 删除 — 改由 mou app (apps/mou/urls.py) 接管
# ============================================================


# ============================================================
# FE URL 错拼 alias
# ============================================================
@_readonly_view(methods=['GET'], resource_code='recruit:talent_pool:menu:view')
def talent_pool_types(request):
    _log_stub_hit('talent_pool_types', request)
    """GET /api/talent-pool/types — FE 错拼双 api 前缀"""
    return _ok([
        {'key': 'EXTERNAL_REFERRAL', 'label': '外推'},
        {'key': 'INTERNAL_TRANSFER', 'label': '内转'},
        {'key': 'PASSIVE', 'label': '被动'},
        {'key': 'SOURCED', 'label': '主动挖掘'},
    ])


@_readonly_view(methods=['GET'], resource_code='recruit:candidate:menu:view')
def resumes_alias(request):
    _log_stub_hit('resumes_alias', request)
    """GET /resumes — FE 错路径, 实际 /scraped-resumes/"""
    return _empty_list()


@_readonly_view(methods=['GET'], resource_code='recruit:candidate:list')
def duplicate_check_list(request):
    _log_stub_hit('duplicate_check_list', request)
    """GET /duplicate-check/ — 拿历史 (FE 期望)"""
    return _empty_list()


# ============================================================
# URL patterns
# ============================================================
urlpatterns = [
    # Auth
    path('auth/register', auth_register, name='auth-register'),
    path('auth/register/', auth_register),
    path('auth/change-password', auth_change_password, name='auth-change-password'),
    path('auth/change-password/', auth_change_password),
    path('login', login_alias, name='login-alias'),
    path('login/', login_alias),

    # Candidate batch
    path('candidates/batch/recommend', candidate_batch_recommend, name='candidate-batch-recommend'),
    path('candidates/batch/recommend/', candidate_batch_recommend),
    path('candidates/batch/archive', candidate_batch_archive, name='candidate-batch-archive'),
    path('candidates/batch/archive/', candidate_batch_archive),
    path('candidates/batch/assign', candidate_batch_assign, name='candidate-batch-assign'),
    path('candidates/batch/assign/', candidate_batch_assign),
    path('candidates/batch/export', candidate_batch_export, name='candidate-batch-export'),
    path('candidates/batch/export/', candidate_batch_export),
    path('candidates/batch/screen', candidate_batch_screen, name='candidate-batch-screen'),
    path('candidates/batch/screen/', candidate_batch_screen),

    # Recruitment process
    path('recruitment-rules/stage-rules', stage_rules, name='recruitment-stage-rules'),
    path('recruitment-rules/stage-rules/', stage_rules),
    path('recruitment-rules/auto-archive-rules', auto_archive_rules, name='recruitment-auto-archive'),
    path('recruitment-rules/auto-archive-rules/', auto_archive_rules),
    path('recruitment-rules/candidates/<str:candidate_id>/evaluate', evaluate_candidate, name='recruitment-evaluate-candidate'),
    path('recruitment-rules/candidates/<str:candidate_id>/evaluate/', evaluate_candidate),
    path('recruitment-rules/applications/<str:application_id>/check-stage-transition', check_stage_transition, name='recruitment-check-stage'),
    path('recruitment-rules/applications/<str:application_id>/check-stage-transition/', check_stage_transition),
    path('recruitment-rules/applications/', _empty_list_view, name='recruitment-applications-list'),
    path('recruitment-rules/applications', _empty_list_view),
    path('recruitment-rules/candidates/', _empty_list_view, name='recruitment-candidates-list'),
    path('recruitment-rules/candidates', _empty_list_view),
    path('recruitment-rules/check-stage-transition', check_stage_transition_no_id, name='recruitment-check-stage-no-id'),
    path('recruitment-rules/check-stage-transition/', check_stage_transition_no_id),
    path('check-stage-transition', check_stage_transition_top, name='check-stage-transition-top'),
    path('check-stage-transition/', check_stage_transition_top),
    path('recruitment-rounds', recruitment_rounds, name='recruitment-rounds'),
    path('recruitment-rounds/', recruitment_rounds),
    path('recruitment-rounds/<str:id>', recruitment_rounds, name='recruitment-rounds-detail'),
    path('recruitment-rounds/<str:id>/', recruitment_rounds),
    path('recruitment-rounds/<str:id>/status', recruitment_rounds_status, name='recruitment-rounds-status'),
    path('recruitment-rounds/<str:id>/status/', recruitment_rounds_status),

    # Add candidate
    path('bulk-create/', bulk_create, name='bulk-create'),
    path('bulk-create', bulk_create),
    path('upload-and-parse/', upload_and_parse, name='upload-and-parse'),
    path('upload-and-parse', upload_and_parse),
    path('scoring/start/', scoring_start, name='scoring-start'),
    path('scoring/start', scoring_start),

    # Offer
    path('offer-templates', offer_templates, name='offer-templates'),
    path('offer-templates/', offer_templates),
    path('offer-templates/render-from-offer', offer_template_render, name='offer-template-render'),
    path('offer-templates/render-from-offer/', offer_template_render),

    # Search
    path('search', global_search, name='global-search'),
    path('search/', global_search),

    # Evaluate
    path('evaluate', evaluate, name='evaluate'),
    path('evaluate/', evaluate),

    # Permissions v1
    path('permissions/roles', permissions_roles_list, name='permissions-roles'),
    path('permissions/roles/', permissions_roles_list),
    path('permissions/users/<str:user_id>/roles', permissions_user_roles, name='permissions-user-roles'),
    path('permissions/users/<str:user_id>/roles/', permissions_user_roles),
    path('permissions/user-info', permissions_user_info, name='permissions-user-info'),
    path('permissions/user-info/', permissions_user_info),
    path('permissions/permissions/list', permissions_list_by_type, name='permissions-list-by-type'),
    path('permissions/permissions/list/', permissions_list_by_type),
    path('permissions/functions', permissions_functions, name='permissions-functions'),
    path('permissions/functions/', permissions_functions),
    path('permissions/menus', permissions_menus, name='permissions-menus'),
    path('permissions/menus/', permissions_menus),
    # 2026-07-02: FE UserManagement.vue 分配MOU 弹窗调
    path('permissions/mous', permissions_mous_list, name='permissions-mous'),
    path('permissions/mous/', permissions_mous_list),
    path('permissions/user-mous/<str:user_id>', permissions_user_mous, name='permissions-user-mous'),
    path('permissions/user-mous/<str:user_id>/', permissions_user_mous),

    # FE URL 错拼 alias — 2026-07-01: FE 已修, 但保留短暂以防客户端缓存
    path('api/talent-pool/types', talent_pool_types, name='api-talent-pool-types'),
    path('api/talent-pool/types/', talent_pool_types),
    path('resumes', resumes_alias, name='resumes-alias'),
    path('resumes/', resumes_alias),

    # Duplicate-check list
    path('duplicate-check/', duplicate_check_list, name='duplicate-check-list'),
    path('duplicate-check', duplicate_check_list),
]
