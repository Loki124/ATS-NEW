"""D1 / D2 —— 看板与抢单池的行级 scope 泄漏回归 (2026-10-21)

**卡 D1｜看板 KPI 接行级 scope**
`apps/analytics/views.py` 的 `dashboard_summary`（docstring 自称「HR **个人**看板」）与
`KpiViewSet.list` 此前是 `Model.objects.filter(deleted_at__isnull=True).count()` 全表计数
→ 任何持 `recruit:settings:data_dashboard:list` 的账号都能读到**全组织**总数,
且与被 scope 裁剪的列表接口两套数字。

**卡 D2｜抢单池接 scope + 修分页 total**
- `apps/application/services/grab.py:GrabService.get_pool` 过滤了 `deleted_at` 但**无 scope**
  → 全公司申请池对所有登录用户可见（列表被裁剪、抢单池不裁剪 = 换个接口就能看别人的申请）。
- `application/views.py` 传 `limit=50` → `grab.py` 先 `[:limit]` 截断 → 再分页
  → `pagination.total` 报的是截断后的条数（恒 ≤ limit）而非真实池总量。

本文件锁死三件事:
1. A 部门账号的看板数字 < 超管（全组织）数字，且只含本部门数据;
2. 跨部门账号在抢单池里看不到他部门申请;
3. `pagination.total` = 真实池总量（不因 limit 截断而失真）。
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.application.models import Application, ApplicationState
from apps.core.models import Department, User
from apps.core.models_permission_v2 import (
    ManagementUnit,
    RolePermissionV2,
    UserRoleV2,
)
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
    StageType,
)

KPI_URL = '/api/v1/data/kpi/'
DASHBOARD_URL = '/api/v1/analytics/exports/dashboard-summary/'
GRAB_POOL_URL = '/api/v1/grab-pool/'

# 两个端点各自的权限码（V2 资源码）——测试用户必须真的持有, 否则 403 测不到 scope。
KPI_CODES = ('recruit:settings:data_dashboard:list',)
GRAB_CODES = ('recruit:candidate:application:list',)


def _make_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


def _make_scoped_user(username, dept_id, role_code, codes):
    """造一个**只看得见 dept_id 部门**的普通账号。

    scope 生效链路: UserRoleV2.app_data_scopes['recruit'] = [管理单元 id]
    → 管理单元 org_scope = [dept_id] → `scope_filter_q` 按 `scope_field__in=[dept_id]` 过滤。
    """
    user = User.objects.create_user(
        username=username, password='Test@1234', department_id=dept_id,
    )
    unit = ManagementUnit.objects.create(
        unit_name=f'{username}-单元', system_code='recruit', unit_type='org',
        org_scope=[dept_id], status=1,
    )
    UserRoleV2.objects.create(
        user=user, role_code=role_code, system_code='recruit',
        app_data_scopes={'recruit': [unit.id]},
    )
    for code in codes:
        RolePermissionV2.objects.create(
            role_code=role_code, resource_code=code, system_code='recruit',
        )
    return user


@pytest.fixture
def dept_a(db):
    return Department.objects.create(
        id='dept-d1-a', name='A 部', code='DEPT_A', path='/A 部',
    )


@pytest.fixture
def dept_b(db):
    return Department.objects.create(
        id='dept-d1-b', name='B 部', code='DEPT_B', path='/B 部',
    )


@pytest.fixture
def user_a(db, dept_a):
    return _make_scoped_user('scope_user_a', dept_a.id, 'R_SCOPE_A', KPI_CODES + GRAB_CODES)


@pytest.fixture
def user_b(db, dept_b):
    return _make_scoped_user('scope_user_b', dept_b.id, 'R_SCOPE_B', KPI_CODES + GRAB_CODES)


@pytest.fixture
def boss(db, dept_a):
    """全组织视角 (超管) —— 作为"能看到全部"的对照组。"""
    return User.objects.create_user(
        username='scope_boss', password='Test@1234',
        department=dept_a, is_staff=True, is_superuser=True,
    )


@pytest.fixture
def referrers(db, dept_a, dept_b):
    """A/B 两部各一个推荐人 —— 候选人的 scope 走 `referrer__department`,
    所以候选人必须挂在**本部**的推荐人名下, 否则 scope 断言测不到东西。"""
    return {
        'a': User.objects.create_user(
            username='scope_ref_a', password='Test@1234', department=dept_a),
        'b': User.objects.create_user(
            username='scope_ref_b', password='Test@1234', department=dept_b),
    }


@pytest.fixture
def positions(db, dept_a, dept_b, boss):
    """A 部 / B 部各一个招聘中的职位。"""
    process = RecruitmentProcess.objects.create(
        id='proc-d1-scope', code='D1_SCOPE', name='scope 流程',
        current_version='1.0', is_template=False, is_enabled=True, is_latest=True,
    )
    out = {}
    for key, dept, code in (('a', dept_a, 'POS_D1_A'), ('b', dept_b, 'POS_D1_B')):
        pos = Position.objects.create(
            id=f'pos-d1-{key}', code=code, title=f'{key} 部职位',
            description='scope 回归', department=dept,
            hiring_manager=boss, owner=boss,
            headcount=1, filled_count=0, state=PositionState.DRAFT, process=process,
        )
        pos.submit_publish()
        pos.save()
        pos.publish()
        pos.save()
        pos.start_recruiting()
        pos.save()
        out[key] = pos
    return out


@pytest.fixture
def applications(db, positions, dept_a, dept_b, boss, referrers):
    """A 部 / B 部各一条在招申请（进抢单池），候选人挂各部推荐人。"""
    process = RecruitmentProcess.objects.get(id='proc-d1-scope')
    stage = RecruitmentStage.objects.create(
        id='stage-d1-scope', code='SD1', name='scope 阶段', stage_type=StageType.SCREEN,
    )
    link = ProcessStageLink.objects.create(
        id='link-d1-scope', process=process, stage=stage, order=1, is_required=True,
    )
    StageRule.objects.create(
        id='rule-d1-scope', link=link, is_grab_mode=True, grab_threshold=30,
    )

    from apps.candidate.models import Candidate

    out = {}
    for key, dept, code in (('a', dept_a, 'APP_D1_A'), ('b', dept_b, 'APP_D1_B')):
        candidate = Candidate.objects.create(
            id=f'cand-d1-{key}', name=f'{key} 部候选人', phone='1390000000' + key,
            referrer=referrers[key],
        )
        out[key] = Application.objects.create(
            id=f'app-d1-{key}', code=code, candidate=candidate,
            position=positions[key], process=process,
            workflow_version=process.current_version,
            state=ApplicationState.ACTIVE,
            current_link=link, current_stage=stage,
            is_grabbed=False,
            stage_entered_at=timezone.now() - timedelta(hours=5),
        )
    return out


# ══════════════════════════════════════════════════════════════════
# 卡 D1 —— 看板接 scope
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestDashboardScope:
    def test_kpi_scoped_by_department(self, user_a, user_b, boss, positions, applications):
        """A 部门账号看到的 KPI 只含本部门; 超管看到全量。"""
        resp_a = _make_client(user_a).get(KPI_URL)
        resp_b = _make_client(user_b).get(KPI_URL)
        resp_boss = _make_client(boss).get(KPI_URL)

        assert resp_a.status_code == 200, resp_a.content
        assert resp_b.status_code == 200, resp_b.content
        assert resp_boss.status_code == 200, resp_boss.content

        kpi_a = resp_a.json()['data']
        kpi_b = resp_b.json()['data']
        kpi_boss = resp_boss.json()['data']

        # 职位：A 账号只看到 A 部的 1 个, 超管看到 2 个
        assert kpi_a['openPositions'] == 1, kpi_a
        assert kpi_b['openPositions'] == 1, kpi_b
        assert kpi_boss['openPositions'] == 2, kpi_boss
        # 候选人: scope 走 referrer__department, 各部候选人分别挂本部推荐人
        assert kpi_a['totalCandidates'] == 1, kpi_a
        assert kpi_b['totalCandidates'] == 1, kpi_b
        assert kpi_boss['totalCandidates'] == 2, kpi_boss

    def test_dashboard_summary_scoped_by_department(self, user_a, user_b, boss, positions, applications):
        """dashboard-summary 同样按部门隔离。

        注意: 响应键经 `djangorestframework-camel-case` 渲染器转成 camelCase
        (源里的 candidates_total → candidatesTotal)。
        """
        resp_a = _make_client(user_a).get(DASHBOARD_URL)
        resp_boss = _make_client(boss).get(DASHBOARD_URL)

        assert resp_a.status_code == 200, resp_a.content
        assert resp_boss.status_code == 200, resp_boss.content

        data_a = resp_a.json()['data']
        data_boss = resp_boss.json()['data']

        assert data_a['applicationsTotal'] == 1, data_a
        assert data_boss['applicationsTotal'] == 2, data_boss
        assert data_a['positionsOpen'] == 1, data_a
        assert data_boss['positionsOpen'] == 2, data_boss
        assert data_a['candidatesTotal'] == 1, data_a
        assert data_boss['candidatesTotal'] == 2, data_boss

    def test_super_admin_still_sees_everything(self, boss, positions, applications):
        """超管不被 scope 裁剪 (数字与改造前一致) —— 防止"修过头"把全量也砍了。"""
        resp = _make_client(boss).get(KPI_URL)
        assert resp.status_code == 200, resp.content
        assert resp.json()['data']['openPositions'] == 2


# ══════════════════════════════════════════════════════════════════
# 卡 D2 —— 抢单池接 scope + 修分页 total
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGrabPoolScope:
    def test_cross_department_application_not_visible(self, user_a, user_b, boss, applications):
        """跨部门账号在抢单池里看不到他部门申请。"""
        resp_a = _make_client(user_a).get(GRAB_POOL_URL)
        resp_b = _make_client(user_b).get(GRAB_POOL_URL)

        assert resp_a.status_code == 200, resp_a.content
        assert resp_b.status_code == 200, resp_b.content

        codes_a = {row['code'] for row in resp_a.json()['data']}
        codes_b = {row['code'] for row in resp_b.json()['data']}
        assert codes_a == {'APP_D1_A'}, codes_a
        assert codes_b == {'APP_D1_B'}, codes_b

    def test_pagination_total_is_real_pool_size(self, user_a, applications):
        """`pagination.total` = 真实池总量, 不因 limit 截断而失真。"""
        # 再塞 3 条同部门申请, 池里共 4 条 (limit 上限 200, 远大于池子)
        from apps.candidate.models import Candidate
        from apps.process.models import ProcessStageLink

        link = ProcessStageLink.objects.get(id='link-d1-scope')
        app_a = applications['a']
        for i in range(3):
            candidate = Candidate.objects.create(
                id=f'cand-d1-extra-{i}', name=f'补位候选人{i}', phone=f'1390000010{i}',
                referrer=None,
            )
            Application.objects.create(
                id=f'app-d1-extra-{i}', code=f'APP_D1_X{i}', candidate=candidate,
                position=app_a.position, process=app_a.process,
                workflow_version=app_a.process.current_version,
                state=ApplicationState.ACTIVE,
                current_link=link, current_stage=app_a.current_stage,
                is_grabbed=False,
                stage_entered_at=timezone.now() - timedelta(hours=5),
            )

        resp = _make_client(user_a).get(GRAB_POOL_URL)
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['pagination']['total'] == 4, body['pagination']

    def test_limit_truncates_page_but_not_total(self, user_a, applications):
        """limit 只裁当页行数, total 仍是真实总量。"""
        from apps.candidate.models import Candidate
        from apps.process.models import ProcessStageLink

        link = ProcessStageLink.objects.get(id='link-d1-scope')
        app_a = applications['a']
        for i in range(3):
            candidate = Candidate.objects.create(
                id=f'cand-d1-lim-{i}', name=f'限位候选人{i}', phone=f'1390000020{i}',
            )
            Application.objects.create(
                id=f'app-d1-lim-{i}', code=f'APP_D1_L{i}', candidate=candidate,
                position=app_a.position, process=app_a.process,
                workflow_version=app_a.process.current_version,
                state=ApplicationState.ACTIVE,
                current_link=link, current_stage=app_a.current_stage,
                is_grabbed=False,
                stage_entered_at=timezone.now() - timedelta(hours=5),
            )

        resp = _make_client(user_a).get(GRAB_POOL_URL, {'limit': 2})
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert len(body['data']) == 2, len(body['data'])
        assert body['pagination']['total'] == 4, body['pagination']

    def test_grab_pool_summary_scoped(self, user_a, user_b, applications):
        """抢单池汇总也按 scope 裁剪 (此前是全公司池子大小)。"""
        resp_a = _make_client(user_a).get(f'{GRAB_POOL_URL}summary/')
        assert resp_a.status_code == 200, resp_a.content
        assert 'total' in resp_a.json(), resp_a.json()
        assert resp_a.json()['total'] == 1, resp_a.json()
