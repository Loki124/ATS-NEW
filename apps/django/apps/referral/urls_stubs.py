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

# === 治理规约（2026-09-04 起）==========================================
# 74 条 path（37 个 endpoint）已在 STUB_CLASSIFICATION.md 建立索引, 分 4 类:
#   A 类: 安全敏感已 501 (auth/register 等) — 保留, 不允许回退到 _ok()
#   B 类: 前端不再调用 — 后续批次清理
#   C 类: 前端在用且已可承接 — 写操作 stub (candidate_batch_*) 已于 2026-09-27 按 R5/R6 返 501,
#        后续批次迁移到对应 app 的真 views.py; GET 空列表分支保留
#   D 类: 前端在用但暂未落地 — 写操作 stub (bulk-create / upload-and-parse / scoring/start) 已于
#        2026-09-27 返 501 (FE 实际走 /candidates/add-candidate/ 真实前缀, 此 root stub 本就不可达)
#
# 任何新增 stub path 必须:
#   1) 在 STUB_CLASSIFICATION.md 同步新增条目
#   2) 安全敏感操作走 _not_implemented() 返 501 (严禁 _ok() 伪装成功)
#   3) 非安全敏感可走 _empty_list_view() / _ok(), 但必须 _log_stub_hit()
#
# 任何删除/迁移 stub path 必须:
#   1) 先在对应 app 实现真 view + 路由, 用 url 优先级或 include 覆盖 stub
#   2) 在 STUB_CLASSIFICATION.md 标 "已迁出" + 关联 commit
#   3) 在 PR 描述里贴 url 优先级证据
# =====================================================================

import logging
import uuid
from django.db import transaction
from django.urls import path
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from apps.core.permissions import ResourceScoped, IsAuthenticatedReadOnly
from apps.core.views_auth import LoginRateThrottle

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
# 2026-09-11: auth_register / auth_change_password 两个 stub 已删除 ——
#   register 由 apps/accounts/views.py:register_view (真实实现) 接管;
#   change-password 由 apps/core/views_auth.py:change_password_view (真实实现) 接管.
#   二者此前长期返 501 + X-Stub:true (R5/R6 安全护栏), 现功能已落地, 护栏升级为
#   "验证真实行为" (见 tests: 注册真建 is_active=False 用户 / 改密真生效).


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
    # 2026-09-27 P0-3 治理: 原 _ok() 伪装 success:true + 假 recommendationId 却一行库都不写
    # (FE api/candidate.ts:69 真实调用)。按 R5/R6 安全收敛规约返 501, 待 candidate app 补真实批量推荐后迁出。
    return _not_implemented('candidate_batch_recommend', request, '批量推荐尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:edit')
def candidate_batch_archive(request):
    return _not_implemented('candidate_batch_archive', request, '批量归档尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:edit')
def candidate_batch_assign(request):
    return _not_implemented('candidate_batch_assign', request, '批量分配招聘官尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:export')
def candidate_batch_export(request):
    return _not_implemented('candidate_batch_export', request, '批量导出尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:edit')
def candidate_batch_screen(request):
    return _not_implemented('candidate_batch_screen', request, '批量初筛尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


# ============================================================
# Recruitment process (G38)
# ============================================================
@_scoped_view(methods=['GET', 'POST'], resource_code='recruit:role:list')
def stage_rules(request):
    if request.method == 'GET':
        return _empty_list()
    # 2026-09-27 P0-3 治理: POST 原伪装 success:true + 假 id 却未落库, 现返 501
    return _not_implemented('stage_rules', request, '阶段规则写入尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


@_scoped_view(methods=['GET', 'POST'], resource_code='recruit:role:list')
def auto_archive_rules(request):
    if request.method == 'GET':
        return _empty_list()
    # 2026-09-27 P0-3 治理: POST 原伪装 success:true + 假 id 却未落库, 现返 501
    return _not_implemented('auto_archive_rules', request, '自动归档规则写入尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


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
    if request.method == 'GET':
        return _empty_list()
    # 2026-09-27 P0-3 治理: POST/PUT 原伪装 success:true + 假 id 却未落库, 现返 501
    return _not_implemented('recruitment_rounds', request, '招聘轮次写入尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


@_scoped_view(methods=['PUT'], resource_code='recruit:application:advance')
def recruitment_rounds_status(request, id):
    return _not_implemented('recruitment_rounds_status', request, '招聘轮次状态变更尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


# ============================================================
# Add candidate: bulk-create, upload-and-parse, scoring
# ============================================================
@_scoped_view(methods=['POST'], resource_code='recruit:candidate:create')
def bulk_create(request):
    # 2026-09-27 P0-3 治理: 原 _ok() 伪装成功却未落库 (FE 实际走 /candidates/add-candidate/bulk-create/ 真实端点, 此 root stub 已不可达)。返 501。
    return _not_implemented('bulk_create', request, '批量创建尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:create')
def upload_and_parse(request):
    return _not_implemented('upload_and_parse', request, '上传并解析尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:create')
def scoring_start(request):
    return _not_implemented('scoring_start', request, '发起评分尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


# ============================================================
# Offer templates
# ============================================================
@_scoped_view(methods=['GET', 'POST'], resource_code='recruit:offer:list')
def offer_templates(request):
    if request.method == 'GET':
        return _empty_list()
    # 2026-09-27 P0-3 治理: POST 原伪装 success:true + 假 id 却未落库, 现返 501
    return _not_implemented('offer_templates', request, 'Offer 模板写入尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


@_scoped_view(methods=['POST'], resource_code='recruit:offer:edit')
def offer_template_render(request):
    return _not_implemented('offer_template_render', request, 'Offer 模板渲染尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


# ============================================================
# Global search + Evaluate
# ============================================================
@_readonly_view(methods=['GET'], resource_code='recruit:candidate:list')
def global_search(request):
    _log_stub_hit('global_search', request)
    return _ok({'candidates': [], 'positions': [], 'demands': [], 'invitations': [], 'total': 0, 'query': request.query_params.get('q', '')})


@_scoped_view(methods=['POST'], resource_code='recruit:candidate:list')
def evaluate(request):
    return _not_implemented('evaluate', request, '候选人评估尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


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


@_scoped_view(methods=['GET', 'POST'], resource_code='recruit:user_role:edit')
def permissions_user_roles(request, user_id):
    _log_stub_hit('permissions_user_roles', request)
    """GET /permissions/users/{id}/roles — 用户的角色
    POST /permissions/users/{id}/roles — 覆盖式保存用户的角色分配 (body {roleIds:[RoleV2.id]})

    T30.175: V1 UserRole 表已 DROP, 改读/写 UserRoleV2 (role_code) + RoleV2.
    2026-09-19: 补 POST 真实现 — 此前 GET-only, 前端「分配角色」弹窗一直 405 失败.
    """
    from apps.core.models_permission_v2 import UserRoleV2, RoleV2
    from apps.core.serializers import RoleSerializer
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return Response(
            {'success': False, 'code': 'bad_request', 'message': 'user_id 非法'},
            status=400,
        )
    if request.method == 'POST':
        # djangorestframework-camel-case 会把入参 roleIds 转成 role_ids, 两者都兼容读取
        role_ids = request.data.get('role_ids') or request.data.get('roleIds') or []
        if not isinstance(role_ids, list):
            return Response(
                {'success': False, 'code': 'validation_error', 'message': 'roleIds 必须是 list'},
                status=400,
            )
        # 2026-09-19 修复: 去掉 status=1 过滤 —— 种子角色 status 多为 None, 该过滤会令
        # role_codes 恒为空 -> 覆盖式清空后不写任何行, POST 谎报 success:true 但实际上没保存。
        # 与列表接口 permissions_roles_list 行为对齐: 仅按 id 取角色。
        roles = list(RoleV2.objects.filter(id__in=role_ids))
        role_codes = [r.role_code for r in roles]
        with transaction.atomic():
            UserRoleV2.objects.filter(user_id=uid, system_code='recruit').delete()
            for rc in role_codes:
                UserRoleV2.objects.get_or_create(
                    user_id=uid,
                    role_code=rc,
                    system_code='recruit',
                    defaults={'granted_by_id': getattr(request.user, 'id', None)},
                )
        data = RoleSerializer(roles, many=True).data
        return Response({'success': True, 'data': data})
    # GET
    role_codes = list(UserRoleV2.objects.filter(
        user_id=uid, system_code='recruit',
    ).values_list('role_code', flat=True).distinct())
    # 2026-09-19 修复: 去掉 status=1 过滤, 与列表/POST 行为对齐 (种子角色 status 多为 None)
    roles = RoleV2.objects.filter(role_code__in=role_codes)
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
    """GET /permissions/user-mous/{user_id} — 用户已分配的 MOU 列表 (mouId 列表).

    2026-07-02: User model 无 mou M2M 字段, 暂返空 list. 真实 G36+ 实现会引入 UserMOU M2M 表.
    """
    if request.method == 'GET':
        # 真有 MOU 表的话, 这里会查 UserMOU 表; 现在返 []
        return Response({'success': True, 'data': []})
    # 2026-09-27 P0-3 治理: POST 原 echo 保存却未落库, 现返 501 (待 UserMOU 表实现)
    return _not_implemented('permissions_user_mous', request, '用户 MOU 分配尚未实现：此前 stub 伪装成功却未落库，现按安全规约返回 501。')


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


# ============================================================
# URL patterns
# ============================================================
urlpatterns = [
    # Auth — 2026-09-11: auth/register 与 auth/change-password 已由真实实现接管
    #   (apps/accounts/views.py register_view + apps/core/views_auth.py change_password_view),
    #   对应 stub 路由与函数已删除, 不再返回 501 假绿.
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

    # FE URL 错拼 alias — 2026-07-01: FE 已修, 但保留短暂以防客户端缓存
    path('api/talent-pool/types', talent_pool_types, name='api-talent-pool-types'),
    path('api/talent-pool/types/', talent_pool_types),
    path('resumes', resumes_alias, name='resumes-alias'),
    path('resumes/', resumes_alias),
]
