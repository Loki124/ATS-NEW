"""FE 期望的 22 个 404 endpoint 一次性 stub (2026-07-01)

FE 调用了但 backend 还没实现的 endpoint, 一律先返合理 stub 避免 404.
等 G30/G35/G36/G40/G41 任务来再补真实 model + 业务逻辑.

Stub 策略:
  - GET 返空 list / 空 data
  - POST 返 {success: true, data: {id: 'stub-uuid'}}
  - PUT/PATCH 返 echo
  - DELETE 返 204
"""
import uuid
from django.urls import path
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status


def _ok(data=None, code=200):
    return Response({'success': True, 'data': data}, status=code)


def _empty_list():
    return Response({'success': True, 'data': [], 'pagination': {'page': 1, 'pageSize': 20, 'total': 0, 'totalPages': 1, 'hasNext': False, 'hasPrevious': False}})


def _empty_data():
    return Response({'success': True, 'data': {}})


# ============================================================
# Auth: register + change-password
# ============================================================
@api_view(['POST'])
@permission_classes([])
def auth_register(request):
    """POST /auth/register — 创建新用户. 2026-07-01 stub: 不实际写, 返 fake id."""
    return _ok({'id': f'user-stub-{uuid.uuid4().hex[:8]}', 'username': request.data.get('username', 'new-user'), 'status': 'ACTIVE'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auth_change_password(request):
    """POST /auth/change-password — 修改自己密码. 2026-07-01 stub."""
    return _ok({'message': '密码已更新 (stub)'})


# ============================================================
# Candidate: 5 个 batch 操作 (G9 PRD)
# ============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_recommend(request):
    """POST /candidates/batch/recommend — 批量推荐到岗位"""
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True, 'recommendationId': f'rec-stub-{uuid.uuid4().hex[:8]}'} for cid in ids]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_archive(request):
    """POST /candidates/batch/archive — 批量归档"""
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True} for cid in ids]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_assign(request):
    """POST /candidates/batch/assign — 批量分配 recruiter"""
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True, 'recruiterId': request.data.get('recruiterId')} for cid in ids]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_export(request):
    """POST /candidates/batch/export — 批量导出 (返个空 blob 占位)"""
    return _ok({'jobId': f'export-stub-{uuid.uuid4().hex[:8]}', 'status': 'PENDING'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_batch_screen(request):
    """POST /candidates/batch/screen — 批量筛选"""
    ids = request.data.get('candidateIds', [])
    return _ok({'results': [{'candidateId': cid, 'success': True, 'result': request.data.get('result', 'PASS')} for cid in ids]})


# ============================================================
# Recruitment process: 6 个 (G38 PRD, 阶段规则/自动归档/面试轮次)
# ============================================================
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def stage_rules(request):
    """GET/POST /recruitment-rules/stage-rules — 阶段规则 CRUD"""
    if request.method == 'GET':
        return _empty_list()
    return _ok({'id': f'sr-stub-{uuid.uuid4().hex[:8]}', **request.data})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def auto_archive_rules(request):
    """GET/POST /recruitment-rules/auto-archive-rules — 自动归档规则"""
    if request.method == 'GET':
        return _empty_list()
    return _ok({'id': f'aar-stub-{uuid.uuid4().hex[:8]}', **request.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluate_candidate(request, candidate_id):
    """GET /recruitment-rules/candidates/{id}/evaluate — 评估候选人进入条件"""
    return _ok({'passed': True, 'failedItems': [], 'prompt': None, 'candidateId': candidate_id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_stage_transition(request, application_id):
    """GET /recruitment-rules/applications/{id}/check-stage-transition — 检查阶段转换"""
    return _ok({'canTransition': True, 'nextStageId': None, 'applicationId': application_id, 'checks': []})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_stage_transition_no_id(request):
    """GET /recruitment-rules/check-stage-transition — 检查阶段转换 (无 applicationId). 2026-07-01 stub."""
    return _ok({'canTransition': True, 'nextStageId': None, 'applicationId': None, 'checks': []})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_stage_transition_top(request):
    """GET /check-stage-transition — 顶层无 prefix 的版本 (FE 期望). 2026-07-01 stub."""
    return _ok({'canTransition': True, 'nextStageId': None, 'applicationId': None, 'checks': []})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def _empty_list_view(request):
    """带 @api_view 的空 list, 避免 500"""
    return _empty_list()


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def recruitment_rounds(request, id=None):
    """GET/POST /recruitment-rounds + /recruitment-rounds/{id} + /recruitment-rounds/{id}/status"""
    if request.method == 'GET':
        return _empty_list()
    if request.method == 'POST':
        return _ok({'id': f'rr-stub-{uuid.uuid4().hex[:8]}', **request.data})
    return _ok({'id': id, 'status': request.data.get('status', 'ACTIVE')})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def recruitment_rounds_status(request, id):
    """PUT /recruitment-rounds/{id}/status"""
    return _ok({'id': id, 'status': request.data.get('status', 'ACTIVE')})


# ============================================================
# Add candidate: 4 个 (bulk-create, upload-and-parse, scoring, login alias)
# ============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_create(request):
    """POST /bulk-create/ — 批量创建候选人"""
    candidates = request.data.get('candidates', [])
    return _ok({'results': [{'success': True, 'id': f'c-stub-{uuid.uuid4().hex[:8]}'} for _ in candidates]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_and_parse(request):
    """POST /upload-and-parse/ — 上传简历 + 解析 (返 job_id)"""
    return _ok({'jobId': f'parse-stub-{uuid.uuid4().hex[:8]}', 'status': 'PENDING', 'fileCount': len(request.FILES)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scoring_start(request):
    """POST /scoring/start/ — 启动评分"""
    return _ok({'jobId': f'score-stub-{uuid.uuid4().hex[:8]}', 'status': 'PENDING'})


# ============================================================
# Offer: 2 个
# ============================================================
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def offer_templates(request):
    """GET/POST /offer-templates — Offer 模板 CRUD"""
    if request.method == 'GET':
        return _empty_list()
    return _ok({'id': f'ot-stub-{uuid.uuid4().hex[:8]}', **request.data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def offer_template_render(request):
    """POST /offer-templates/render-from-offer — 从 offer 渲染模板"""
    return _ok({'fileUrl': f'https://stub.example.com/render-{uuid.uuid4().hex[:8]}.pdf', 'format': request.data.get('format', 'pdf')})


# ============================================================
# Search
# ============================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def global_search(request):
    """GET /search — 全局搜索 (FE 搜素框). 返空 stub."""
    return _ok({
        'candidates': [], 'positions': [], 'demands': [], 'invitations': [],
        'total': 0, 'query': request.query_params.get('q', ''),
    })


# ============================================================
# Evaluate (无 candidate id 的 evaluate)
# ============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def evaluate(request):
    """POST /evaluate — 通用评估"""
    return _ok({'score': 0, 'passed': False, 'details': []})


# ============================================================
# Login alias (单数) — 直接走 standardlogin view
# ============================================================
@api_view(['POST'])
@permission_classes([])
def login_alias(request):
    """POST /login — 委托给 standard auth login"""
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
            'user': {
                'id': user.id,
                'username': user.username,
                'isStaff': user.is_staff,
            }
        }
    })


urlpatterns = [
    # Auth
    path('auth/register', auth_register, name='auth-register'),
    path('auth/register/', auth_register),
    path('auth/change-password', auth_change_password, name='auth-change-password'),
    path('auth/change-password/', auth_change_password),

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

    # Duplicate-check list (FE 调 /duplicate-check/ 拿历史)
    path('duplicate-check/', _empty_list_view, name='duplicate-check-list'),
    path('duplicate-check', _empty_list_view),

    # Login alias
    path('login', login_alias, name='login-alias'),
    path('login/', login_alias),
]
