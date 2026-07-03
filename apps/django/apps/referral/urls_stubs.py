"""FE 期望的 stub endpoint 兜底 (2026-07-01)

合并第一批 (auth/candidate batch/recruitment-process/offer-template/scoring/upload-parse)
+ 第二批 (permissions/permissions-v2/talent-pool/resumes 等).

所有 endpoint 一律返合理 stub 避免 404:
  - GET 返空 list / 空 data
  - POST 返 {success: true, data: {id: 'stub-uuid'}}
  - PUT/PATCH 返 echo
"""
import uuid
from django.urls import path
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes


def _ok(data=None, code=200):
    return Response({'success': True, 'data': data}, status=code)


def _empty_list():
    return Response({'success': True, 'data': [], 'pagination': {'page': 1, 'pageSize': 20, 'total': 0, 'totalPages': 1, 'hasNext': False, 'hasPrevious': False}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def _empty_list_view(request):
    return _empty_list()


# ============================================================
# Auth
# ============================================================
@api_view(['POST'])
@permission_classes([])
def auth_register(request):
    return _ok({'id': f'user-stub-{uuid.uuid4().hex[:8]}', 'username': request.data.get('username', 'new-user'), 'status': 'ACTIVE'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auth_change_password(request):
    return _ok({'message': '密码已更新 (stub)'})


# ============================================================
# Login alias (单数) — POST /login
# ============================================================
@api_view(['POST'])
@permission_classes([])
def login_alias(request):
    from django.contrib.auth import authenticate
    from rest_framework_simplejwt.tokens import RefreshToken
    user = authenticate(username=request.data.get('username', ''), password=request.data.get('password', ''))
    if user is None:
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
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_recommend(request):
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True, 'recommendationId': f'rec-stub-{uuid.uuid4().hex[:8]}'} for cid in ids]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_archive(request):
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True} for cid in ids]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_assign(request):
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True, 'recruiterId': request.data.get('recruiterId')} for cid in ids]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_export(request):
    return _ok({'jobId': f'export-stub-{uuid.uuid4().hex[:8]}', 'status': 'PENDING'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_screen(request):
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True, 'result': request.data.get('result', 'PASS')} for cid in ids]})


# ============================================================
# Recruitment process (G38)
# ============================================================
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def stage_rules(request):
    if request.method == 'GET':
        return _empty_list()
    return _ok({'id': f'sr-stub-{uuid.uuid4().hex[:8]}', **request.data})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def auto_archive_rules(request):
    if request.method == 'GET':
        return _empty_list()
    return _ok({'id': f'aar-stub-{uuid.uuid4().hex[:8]}', **request.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluate_candidate(request, candidate_id):
    return _ok({'passed': True, 'failedItems': [], 'prompt': None, 'candidateId': candidate_id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_stage_transition(request, application_id):
    return _ok({'canTransition': True, 'nextStageId': None, 'applicationId': application_id, 'checks': []})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_stage_transition_no_id(request):
    return _ok({'canTransition': True, 'nextStageId': None, 'applicationId': None, 'checks': []})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_stage_transition_top(request):
    return _ok({'canTransition': True, 'nextStageId': None, 'applicationId': None, 'checks': []})


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def recruitment_rounds(request, id=None):
    if request.method == 'GET':
        return _empty_list()
    if request.method == 'POST':
        return _ok({'id': f'rr-stub-{uuid.uuid4().hex[:8]}', **request.data})
    return _ok({'id': id, 'status': request.data.get('status', 'ACTIVE')})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def recruitment_rounds_status(request, id):
    return _ok({'id': id, 'status': request.data.get('status', 'ACTIVE')})


# ============================================================
# Add candidate: bulk-create, upload-and-parse, scoring
# ============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_create(request):
    candidates = request.data.get('candidates', [])
    return _ok({'results': [{'success': True, 'id': f'c-stub-{uuid.uuid4().hex[:8]}'} for _ in candidates]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_and_parse(request):
    return _ok({'jobId': f'parse-stub-{uuid.uuid4().hex[:8]}', 'status': 'PENDING', 'fileCount': len(request.FILES)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scoring_start(request):
    return _ok({'jobId': f'score-stub-{uuid.uuid4().hex[:8]}', 'status': 'PENDING'})


# ============================================================
# Offer templates
# ============================================================
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def offer_templates(request):
    if request.method == 'GET':
        return _empty_list()
    return _ok({'id': f'ot-stub-{uuid.uuid4().hex[:8]}', **request.data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def offer_template_render(request):
    return _ok({'fileUrl': f'https://stub.example.com/render-{uuid.uuid4().hex[:8]}.pdf', 'format': request.data.get('format', 'pdf')})


# ============================================================
# Global search + Evaluate
# ============================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def global_search(request):
    return _ok({'candidates': [], 'positions': [], 'demands': [], 'invitations': [], 'total': 0, 'query': request.query_params.get('q', '')})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def evaluate(request):
    return _ok({'score': 0, 'passed': False, 'details': []})


# ============================================================
# Permissions v1 (FE 期望 /permissions/* 走这里)
# 2026-07-01: 已有 Role/Permission model, 这些是 alias 调真 endpoint
# ============================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permissions_roles_list(request):
    """GET /permissions/roles/ — 角色列表 (alias 调 /roles/)"""
    from apps.core.models import Role
    from apps.core.serializers import RoleSerializer
    qs = Role.objects.filter(is_active=True)
    search = request.query_params.get('search', '')
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)
    data = RoleSerializer(qs[:50], many=True).data
    return Response({'success': True, 'data': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permissions_user_roles(request, user_id):
    """GET /permissions/users/{id}/roles — 用户的角色 (调 UserRole)"""
    from apps.core.models import UserRole, Role
    user_role_ids = UserRole.objects.filter(user_id=user_id).values_list('role_id', flat=True)
    roles = Role.objects.filter(id__in=user_role_ids, is_active=True)
    from apps.core.serializers import RoleSerializer
    data = RoleSerializer(roles, many=True).data
    return Response({'success': True, 'data': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permissions_user_info(request):
    """GET /permissions/user-info/ — 当前用户权限 + 角色"""
    from apps.core.models import UserRole, Role
    user = request.user
    user_role_ids = UserRole.objects.filter(user_id=user.id).values_list('role_id', flat=True)
    roles = Role.objects.filter(id__in=user_role_ids, is_active=True)
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permissions_list_by_type(request):
    """GET /permissions/permissions/list?type=MENU|FUNCTION|DATA — 权限字典
    2026-07-02: 跟随业务字典命名 (`:read`/`:export` 是菜单, `:create|:update|:delete|:approve|:assign` 是功能)
    """
    from apps.core.models import Permission
    from apps.core.serializers import PermissionSerializer
    qs = Permission.objects.all()
    type_filter = request.query_params.get('type', '')
    if type_filter == 'MENU':
        # 菜单权限: 读类 (排除写操作后缀)
        qs = qs.filter(code__endswith=':read') | qs.filter(code__endswith=':export')
    elif type_filter == 'FUNCTION':
        # 功能权限: 写操作 (创建/编辑/删除/审批/分配)
        from django.db.models import Q
        qs = qs.filter(
            Q(code__endswith=':create') |
            Q(code__endswith=':update') |
            Q(code__endswith=':delete') |
            Q(code__endswith=':approve') |
            Q(code__endswith=':assign')
        )
    elif type_filter == 'DATA':
        # 数据权限: 暂用 system:admin 占位, 业务侧真正 data scope 待 G37+ 实现
        qs = qs.filter(code='system:admin')
    elif type_filter == 'API':
        qs = qs.filter(module__icontains='api')
    data = PermissionSerializer(qs[:200], many=True).data
    return Response({'success': True, 'data': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permissions_functions(request):
    """GET /permissions/functions/ — 功能权限 (写操作)"""
    from apps.core.models import Permission
    from apps.core.serializers import PermissionSerializer
    from django.db.models import Q
    qs = Permission.objects.filter(
        Q(code__endswith=':create') |
        Q(code__endswith=':update') |
        Q(code__endswith=':delete') |
        Q(code__endswith=':approve') |
        Q(code__endswith=':assign')
    )[:200]
    data = PermissionSerializer(qs, many=True).data
    return Response({'success': True, 'data': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permissions_menus(request):
    """GET /permissions/menus/ — 菜单/读权限"""
    from apps.core.models import Permission
    from apps.core.serializers import PermissionSerializer
    from django.db.models import Q
    qs = Permission.objects.filter(
        Q(code__endswith=':read') | Q(code__endswith=':export')
    ).distinct()[:200]
    data = PermissionSerializer(qs, many=True).data
    return Response({'success': True, 'data': data})


# ============================================================
# 2026-07-01 花无缺: permissions-v2/* 5 个 stub view 删除 — 改由 mou app (apps/mou/urls.py) 接管
# ============================================================


# ============================================================
# FE URL 错拼 alias
# ============================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def talent_pool_types(request):
    """GET /api/talent-pool/types — FE 错拼双 api 前缀"""
    return _ok([
        {'key': 'EXTERNAL_REFERRAL', 'label': '外推'},
        {'key': 'INTERNAL_TRANSFER', 'label': '内转'},
        {'key': 'PASSIVE', 'label': '被动'},
        {'key': 'SOURCED', 'label': '主动挖掘'},
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resumes_alias(request):
    """GET /resumes — FE 错路径, 实际 /scraped-resumes/"""
    return _empty_list()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def duplicate_check_list(request):
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

    # FE URL 错拼 alias — 2026-07-01: FE 已修, 但保留短暂以防客户端缓存
    path('api/talent-pool/types', talent_pool_types, name='api-talent-pool-types'),
    path('api/talent-pool/types/', talent_pool_types),
    path('resumes', resumes_alias, name='resumes-alias'),
    path('resumes/', resumes_alias),

    # Duplicate-check list
    path('duplicate-check/', duplicate_check_list, name='duplicate-check-list'),
    path('duplicate-check', duplicate_check_list),
]
