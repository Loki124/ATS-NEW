"""非空表回归测试 — GET /api/v1/applications/ 与 GET /api/v1/grab-pool/

背景 (commit a78020a, 2026-08-06)
================================
8 处 DRF DefaultRouter 路由掩盖修复后，暴露了 3 个此前被"路由不可达"掩盖的二级 bug。
其中 2 个直接影响本文件覆盖的两个端点：

1. ``ApplicationListSerializer.get_is_in_grab_pool`` 引用了
   ``Application.ApplicationState.ACTIVE``。但 ``ApplicationState`` 是
   ``apps/application/models.py`` 的**模块级** ``TextChoices``，不是 ``Application``
   的内部类 → ``AttributeError``。
   ⚠️ 关键：``get_is_in_grab_pool`` 是 ``SerializerMethodField``，**只在有行要序列化时
   才执行**。测试库 applications 表为空 → 该方法从不执行 → 端点稳返 200 → bug 长期
   隐身。只要生产库有一条申请记录，``GET /api/v1/applications/`` 必 500。

2. ``GrabPoolViewSet`` 原继承 ``viewsets.ViewSet``（APIView 系，**没有**
   ``paginate_queryset`` / ``get_paginated_response``，那两个方法来自 GenericAPIView）
   → ``list()`` 里的 ``self.paginate_queryset(apps)`` 必 ``AttributeError`` → 500。
   已改继承 ``viewsets.GenericViewSet``。

3. ``get_is_in_grab_pool`` 的 ``and`` 链中途短路时返回 ``None`` / 模型实例而非 ``bool``，
   与 ``-> bool`` 注解（drf-spectacular 据此生成 schema）不符 → 前端拿到 ``null``
   而不是 ``false``。已用 ``bool()`` 包裹。

本文件的设计原则
================
**空表跑测试等于没测生产路径。** 因此这里的每个用例都先造真实数据（完整外键链
Department → Process → Stage → StageLink → StageRule → Position → Candidate →
Application），再打真实 HTTP 端点，确保 SerializerMethodField 与分页器真的被执行。

数据集（3 条申请，覆盖 and 链的 3 条不同路径）：
  - APP-GRAB-001  ACTIVE / 未认领 / link 挂 is_grab_mode=True  → is_in_grab_pool=True （全链走通）
  - APP-GRAB-002  ACTIVE / 未认领 / current_link=None          → is_in_grab_pool=False（**短路**，旧代码返 None）
  - APP-GRAB-003  ACTIVE / 已认领                              → is_in_grab_pool=False（短路于 not is_grabbed）
"""
import pytest

from apps.application.models import Application, ApplicationState
from apps.candidate.models import Candidate
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
    StageType,
)

APPLICATIONS_URL = '/api/v1/applications/'
GRAB_POOL_URL = '/api/v1/grab-pool/'


# ============================================================
# Fixtures — 完整外键链，保证 applications 表非空
# ============================================================
@pytest.fixture
def grab_process(db):
    return RecruitmentProcess.objects.create(
        id='proc-grabpool-regression',
        code='GRABPOOL_REGRESSION',
        name='抢单池回归测试流程',
        current_version='1.0',
        is_template=False,
        is_enabled=True,
    )


@pytest.fixture
def grab_stage(db):
    """抢单模式阶段（stage_type=SCREEN，初筛常见抢单场景）。"""
    return RecruitmentStage.objects.create(
        id='stage-grabpool-regression',
        code='PGRAB901',
        name='抢单回归阶段',
        stage_type=StageType.SCREEN,
    )


@pytest.fixture
def grab_link(db, grab_process, grab_stage):
    """流程-阶段关联，并挂一条 is_grab_mode=True 的 StageRule。"""
    link = ProcessStageLink.objects.create(
        id='link-grabpool-regression',
        process=grab_process,
        stage=grab_stage,
        order=1,
        is_required=True,
    )
    StageRule.objects.create(
        id='rule-grabpool-regression',
        link=link,
        is_grab_mode=True,
        grab_threshold=30,
    )
    return link


@pytest.fixture
def grab_position(db, department, super_user, grab_process):
    """招聘中的职位。department / super_user 复用公共 fixture，
    使超管 scope bypass 与数据部门一致，排除 IDOR 过滤干扰。
    """
    pos = Position.objects.create(
        id='pos-grabpool-regression',
        code='P_GRABPOOL_REG',
        title='抢单回归测试职位',
        description='用于验证 applications / grab-pool 端点非空表行为',
        department=department,
        hiring_manager=super_user,
        owner=super_user,
        headcount=3,
        filled_count=0,
        state=PositionState.DRAFT,
        process=grab_process,
    )
    # DRAFT → PENDING_PUBLISH → PUBLISHED → RECRUITING
    pos.submit_publish()
    pos.save()
    pos.publish()
    pos.save()
    pos.start_recruiting()
    pos.save()
    return pos


@pytest.fixture
def grab_candidates(db):
    return [
        Candidate.objects.create(id='cand-grab-001', name='抢单候选人一', phone='13900000001'),
        Candidate.objects.create(id='cand-grab-002', name='抢单候选人二', phone='13900000002'),
        Candidate.objects.create(id='cand-grab-003', name='抢单候选人三', phone='13900000003'),
    ]


@pytest.fixture
def seeded_applications(db, grab_position, grab_process, grab_stage, grab_link,
                        grab_candidates, super_user):
    """造 3 条申请，覆盖 get_is_in_grab_pool 的 3 条求值路径。

    返回 dict: code -> Application
    """
    c1, c2, c3 = grab_candidates

    in_pool = Application.objects.create(
        code='APP-GRAB-001',
        candidate=c1,
        position=grab_position,
        process=grab_process,
        workflow_version=grab_process.current_version,
        state=ApplicationState.ACTIVE,
        current_link=grab_link,
        current_stage=grab_stage,
        is_grabbed=False,
    )
    # current_link=None → 旧代码 and 链短路返回 None（非 bool），是 bug#3 的靶子
    no_link = Application.objects.create(
        code='APP-GRAB-002',
        candidate=c2,
        position=grab_position,
        process=grab_process,
        workflow_version=grab_process.current_version,
        state=ApplicationState.ACTIVE,
        current_link=None,
        current_stage=None,
        is_grabbed=False,
    )
    already_grabbed = Application.objects.create(
        code='APP-GRAB-003',
        candidate=c3,
        position=grab_position,
        process=grab_process,
        workflow_version=grab_process.current_version,
        state=ApplicationState.ACTIVE,
        current_link=grab_link,
        current_stage=grab_stage,
        is_grabbed=True,
        grabbed_by=super_user,
    )
    return {a.code: a for a in (in_pool, no_link, already_grabbed)}


def _items(response):
    """从统一分页响应体里取列表数据。"""
    body = response.json()
    assert 'data' in body, f'响应缺少 data 字段: {body}'
    return body['data']


def _by_code(items):
    return {it['code']: it for it in items}


# ============================================================
# GET /api/v1/applications/ — 非空表
# ============================================================
@pytest.mark.django_db
class TestApplicationsListNonEmpty:
    """核心：证明 applications 表非空时该端点不再 500。"""

    def test_list_returns_200_when_table_not_empty(self, auth_client, seeded_applications):
        """Bug#1 主回归：旧代码在这里必 500（Application.ApplicationState AttributeError）。"""
        assert Application.objects.count() >= 3, '前置条件失败：表必须非空，否则本用例没有意义'

        resp = auth_client.get(APPLICATIONS_URL)

        assert resp.status_code == 200, (
            f'GET {APPLICATIONS_URL} 在表非空时返回 {resp.status_code}，'
            f'期望 200。响应: {resp.content[:800]}'
        )
        assert len(_items(resp)) >= 3

    def test_is_in_grab_pool_field_present_and_boolean_for_every_row(
        self, auth_client, seeded_applications,
    ):
        """每一行都必须有 isInGrabPool，且类型严格为 bool（不能是 null）。"""
        resp = auth_client.get(APPLICATIONS_URL)
        assert resp.status_code == 200

        items = _items(resp)
        assert items, '列表为空，SerializerMethodField 不会被执行，用例失去意义'

        for item in items:
            assert 'isInGrabPool' in item, (
                f"响应项缺少 camelCase 字段 isInGrabPool: {sorted(item.keys())}"
            )
            value = item['isInGrabPool']
            assert type(value) is bool, (
                f"申请 {item.get('code')} 的 isInGrabPool={value!r} "
                f"(type={type(value).__name__})，期望严格 bool"
            )

    def test_is_in_grab_pool_true_when_stage_is_grab_mode(self, auth_client, seeded_applications):
        """and 链全程走通的正路径：ACTIVE + 未认领 + stage_rule.is_grab_mode=True。"""
        resp = auth_client.get(APPLICATIONS_URL)
        assert resp.status_code == 200

        item = _by_code(_items(resp))['APP-GRAB-001']
        assert item['isInGrabPool'] is True

    def test_is_in_grab_pool_is_false_not_null_when_current_link_missing(
        self, auth_client, seeded_applications,
    ):
        """Bug#3 主回归：current_link=None 时 and 链短路。

        修复前返回 ``None`` → JSON ``null``；修复后 ``bool()`` 包裹 → ``false``。
        """
        resp = auth_client.get(APPLICATIONS_URL)
        assert resp.status_code == 200

        item = _by_code(_items(resp))['APP-GRAB-002']
        assert item['isInGrabPool'] is not None, 'and 链短路返回了 null，bool() 包裹失效'
        assert item['isInGrabPool'] is False

    def test_is_in_grab_pool_false_when_already_grabbed(self, auth_client, seeded_applications):
        resp = auth_client.get(APPLICATIONS_URL)
        assert resp.status_code == 200

        item = _by_code(_items(resp))['APP-GRAB-003']
        assert item['isInGrabPool'] is False

    def test_detail_endpoint_still_reachable(self, auth_client, seeded_applications):
        """路由拆分后详情路由未被顶层 grab-pool 抢走。"""
        app = seeded_applications['APP-GRAB-001']
        resp = auth_client.get(f'{APPLICATIONS_URL}{app.id}/')
        assert resp.status_code == 200, resp.content[:500]

    def test_serializer_resolves_module_level_application_state(self):
        """根因守卫：serializers 里的 ApplicationState 必须是 models 的模块级 TextChoices。

        不是 Application 的内部类 —— 这正是 Bug#1 的根因。
        """
        from apps.application import models as app_models
        from apps.application import serializers as app_serializers

        assert app_serializers.ApplicationState is app_models.ApplicationState
        assert not hasattr(Application, 'ApplicationState'), (
            'Application 上不应存在 ApplicationState 属性；若确需别名，'
            '请同步修订本断言并复核所有 Application.ApplicationState 引用点'
        )


# ============================================================
# GET /api/v1/grab-pool/ — 非空表 + 分页
# ============================================================
# ============================================================
# candidatePhone 语义一致性 — applications vs grab-pool（2026-08-07 寇豆码）
# ============================================================
# 根因回归: GrabPoolViewSet.list() 此前裸实例化 ApplicationListSerializer 不带
# context，get_candidate_phone 取不到 request.user → 对所有人都走脱敏分支。
# 而 ApplicationViewSet.list()（DRF ListModelMixin 走 self.get_serializer）带 context，
# 超管可见全号。两端对同一条 Application 返的 candidatePhone 不一致，是同一根因。
# 下面两条用例把"同一条 Application 在两端 candidatePhone 必须相等"锁死：
#   - 超管: 两端都应是全号，相等
#   - 非超管(HR): 两端都应脱敏，相等
# 只要将来脱敏规则或 context 注入再分叉，用例立刻红。
REASSIGN_URL = '/api/v1/grab-pool/reassign/'


@pytest.mark.django_db
class TestCandidatePhoneParity:
    """同一条 Application，applications 与 grab-pool 端点 candidatePhone 必须一致。"""

    def test_super_admin_sees_full_phone_and_parity(self, auth_client, seeded_applications):
        """核心回归（修复后变绿、回退修复变红）。

        超管在两个端点都应看到完整号码，且两值必须相等。
        修复前 grab-pool 端点因缺 context 返回 '139****0001'，与 applications 的
        '13900000001' 分叉 → 此断言失败。
        """
        app = seeded_applications['APP-GRAB-001']
        assert app.candidate.phone == '13900000001'

        resp_apps = auth_client.get(APPLICATIONS_URL)
        resp_pool = auth_client.get(GRAB_POOL_URL)
        assert resp_apps.status_code == 200, resp_apps.content[:500]
        assert resp_pool.status_code == 200, resp_pool.content[:500]

        apps_phone = _by_code(_items(resp_apps))['APP-GRAB-001']['candidatePhone']
        pool_phone = _by_code(_items(resp_pool))['APP-GRAB-001']['candidatePhone']

        # 超管可见完整号码
        assert apps_phone == '13900000001', (
            f'applications 端点超管应见全号，实际: {apps_phone}'
        )
        # 两端语义必须一致（这是本次要修的分叉）
        assert pool_phone == apps_phone, (
            f'candidatePhone 两端不一致: applications={apps_phone!r} '
            f'grab-pool={pool_phone!r}（context 未注入根因未修复）'
        )

    def test_non_admin_sees_masked_phone_and_parity(self, auth_hr_client, seeded_applications):
        """证明修复没有把脱敏整个关掉。

        非超管(HR)在两个端点都应看到脱敏号码，且两端一致。
        注意: 这条对"缺 context"的 bug 不敏感（非超管本就脱敏，缺不缺 context 都脱敏），
        它守卫的是"修复没有误关脱敏逻辑"——若有人顺手改掉 get_candidate_phone 的
        脱敏分支，此断言会红。
        """
        resp_apps = auth_hr_client.get(APPLICATIONS_URL)
        resp_pool = auth_hr_client.get(GRAB_POOL_URL)
        assert resp_apps.status_code == 200, resp_apps.content[:500]
        assert resp_pool.status_code == 200, resp_pool.content[:500]

        apps_phone = _by_code(_items(resp_apps))['APP-GRAB-001']['candidatePhone']
        pool_phone = _by_code(_items(resp_pool))['APP-GRAB-001']['candidatePhone']

        # 非超管必须脱敏
        assert apps_phone != '13900000001', '非超管不应看到完整手机号（脱敏被关掉？）'
        assert '*' in apps_phone, f'预期掩码号码含 *，实际: {apps_phone}'
        # 两端一致
        assert pool_phone == apps_phone, (
            f'脱敏后两端仍不一致: applications={apps_phone!r} grab-pool={pool_phone!r}'
        )


@pytest.mark.django_db
class TestGrabPoolReassignSmoke:
    """reassign 端点此前路由不可达，从上线至今从未执行、覆盖率 0%。

    管理员批量改数据的端点，裸奔风险高。这里只做冒烟：证明它被真实执行过一次且不 500。
    不追求全分支覆盖。
    """

    def test_reassign_endpoint_executes_without_500(self, auth_client):
        """POST /api/v1/grab-pool/reassign/ 应 200，且返回 reassignedCount 字段。

        测试库无超时申请（seed 数据未设 stage_entered_at），reassign_overdue 查不到
        超时项 → results 空 → reassignedCount=0。关键在于端点真的跑通、没抛 500。

        注：响应经 DRF camelCase 渲染器输出，键为 reassignedCount（非 reassigned_count）。
        """
        resp = auth_client.post(
            REASSIGN_URL, {'threshold_minutes': 30}, format='json',
        )
        assert resp.status_code != 500, (
            f'reassign 端点 500: {resp.status_code} body={resp.content[:800]}'
        )
        assert resp.status_code == 200, (
            f'预期 reassign 返回 200，实际 {resp.status_code}: {resp.content[:800]}'
        )
        body = resp.json()
        assert 'reassignedCount' in body, f'响应缺少 reassignedCount: {body}'
        assert body['reassignedCount'] == 0, (
            f'测试库无超时申请，reassignedCount 应为 0，实际 {body}'
        )


@pytest.mark.django_db
class TestGrabPoolListNonEmpty:
    """核心：证明 GrabPoolViewSet 改继承 GenericViewSet 后分页真的能用。"""

    def test_grab_pool_returns_200_with_data(self, auth_client, seeded_applications):
        """Bug#2 主回归：旧代码 paginate_queryset 触发 AttributeError → 500。"""
        resp = auth_client.get(GRAB_POOL_URL)

        assert resp.status_code == 200, (
            f'GET {GRAB_POOL_URL} 返回 {resp.status_code}，期望 200。'
            f'响应: {resp.content[:800]}'
        )
        assert len(_items(resp)) >= 1, '抢单池为空，分页路径未被真正执行'

    def test_grab_pool_response_has_pagination_envelope(self, auth_client, seeded_applications):
        """断言 StandardResultsSetPagination 的完整信封结构（camelCase 输出）。"""
        resp = auth_client.get(GRAB_POOL_URL)
        assert resp.status_code == 200

        body = resp.json()
        assert body.get('success') is True
        assert isinstance(body.get('data'), list)

        pagination = body.get('pagination')
        assert isinstance(pagination, dict), (
            f'响应缺少 pagination 结构，说明 paginate_queryset 未生效: {body}'
        )
        for key in ('page', 'pageSize', 'total', 'totalPages', 'hasNext', 'hasPrevious'):
            assert key in pagination, f'分页信封缺少 {key}: {pagination}'

        assert pagination['page'] == 1
        assert pagination['total'] == 2, '池中应为 APP-GRAB-001 / APP-GRAB-002 两条'

    def test_grab_pool_excludes_grabbed_application(self, auth_client, seeded_applications):
        resp = auth_client.get(GRAB_POOL_URL)
        assert resp.status_code == 200

        codes = {it['code'] for it in _items(resp)}
        assert 'APP-GRAB-001' in codes
        assert 'APP-GRAB-002' in codes
        assert 'APP-GRAB-003' not in codes, '已认领的申请不应出现在抢单池'

    def test_grab_pool_pagination_actually_slices(self, auth_client, seeded_applications):
        """page_size=1 时真的只返回 1 条并给出翻页信息 —— 证明分页器不是摆设。"""
        resp = auth_client.get(GRAB_POOL_URL, {'page_size': 1})
        assert resp.status_code == 200

        body = resp.json()
        assert len(body['data']) == 1, f"page_size=1 却返回 {len(body['data'])} 条"

        pagination = body['pagination']
        assert pagination['pageSize'] == 1
        assert pagination['total'] == 2
        assert pagination['totalPages'] == 2
        assert pagination['hasNext'] is True
        assert pagination['hasPrevious'] is False

    def test_grab_pool_second_page_reachable(self, auth_client, seeded_applications):
        resp = auth_client.get(GRAB_POOL_URL, {'page_size': 1, 'page': 2})
        assert resp.status_code == 200

        body = resp.json()
        assert len(body['data']) == 1
        assert body['pagination']['page'] == 2
        assert body['pagination']['hasPrevious'] is True

    def test_grab_pool_items_carry_boolean_is_in_grab_pool(self, auth_client, seeded_applications):
        """抢单池复用 ApplicationListSerializer，同样不能吐 null。"""
        resp = auth_client.get(GRAB_POOL_URL)
        assert resp.status_code == 200

        for item in _items(resp):
            assert type(item['isInGrabPool']) is bool, (
                f"{item.get('code')} isInGrabPool={item['isInGrabPool']!r}"
            )

    def test_grab_pool_summary_action_reachable(self, auth_client, seeded_applications):
        """summary 子路由此前被 ApplicationViewSet 的 detail 正则吃掉。"""
        resp = auth_client.get(f'{GRAB_POOL_URL}summary/')
        assert resp.status_code == 200, resp.content[:500]
        assert isinstance(resp.json(), dict)
