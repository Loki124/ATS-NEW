"""G1 修复回归：审批码在 offer/demand transition 端点真实生效。

修复前：transition 作为自定义 action 一律按派生码 recruit:offer:edit /
recruit:demand:edit 校验，seed 里定义的
recruit:offer:approve(_l1/_l2) / recruit:demand:approve 后端零消费 ——
身份管理里单独勾「审批Offer / 审批需求」不生效。

修复后：
  - 类级 permission_required_map 放行持有 approve/edit 任一码的请求进入 action；
  - action 内按 FSM 动作细查：approve/reject → 审批码，其余动作 → :edit 码。

测试策略：
  - offer 侧对象图重（application/candidate/position 三重 FK），只做接线断言 +
    has_perm 矩阵（审批码持有者 / 仅 edit 持有者的判定位）；
  - demand 侧对象创建轻，补 HTTP 黑盒：仅 edit 身份审批 → 403，
    仅 approve 身份审批 → 200 流转成功，仅 approve 身份做非审批动作 → 403。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models_permission_v2 import RolePermissionV2
from apps.core.permission_check import has_perm
from tests.fixtures_common import _attach_role, _create_role_v2

from apps.demand.models import Demand, DemandState
from apps.demand.services import DemandCreateData, DemandService
from apps.demand.views import DemandViewSet
from apps.offer.views import OfferViewSet


def _make_scoped_user(department, username: str, codes: tuple[str, ...]):
    """创建一个挂自定义角色（仅持有 codes）的用户，用于细粒度权限断言."""
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password='Test@1234',
        employee_id=username.upper()[:20],
        department=department,
    )
    role = _create_role_v2(f'CUST_{username.upper()}'[:64], username)
    _attach_role(user, role)
    RolePermissionV2.objects.bulk_create([
        RolePermissionV2(role_code=role.role_code, resource_code=c, system_code='recruit')
        for c in codes
    ])
    return user


def _client_for(user) -> APIClient:
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


# ---------------------------------------------------------------------------
# 接线断言：map / FSM 动作映射不被误删
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApproveWiring:
    def test_offer_transition_map_declares_approve(self):
        assert set(OfferViewSet.permission_required_map['transition']) == {
            'recruit:candidate:offer:approve', 'recruit:candidate:offer:edit',
        }
        assert OfferViewSet.TRANSITION_ACTION_PERM['approve'] == 'recruit:candidate:offer:approve'
        assert OfferViewSet.TRANSITION_ACTION_PERM['reject'] == 'recruit:candidate:offer:approve'

    def test_demand_transition_map_declares_approve(self):
        assert set(DemandViewSet.permission_required_map['transition']) == {
            'recruit:demand:approve', 'recruit:demand:edit',
        }
        assert DemandViewSet.TRANSITION_ACTION_PERM['approve'] == 'recruit:demand:approve'
        assert DemandViewSet.TRANSITION_ACTION_PERM['reject'] == 'recruit:demand:approve'


# ---------------------------------------------------------------------------
# has_perm 矩阵：审批码 / edit 码互不包含
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApprovePermMatrix:
    def test_approve_holder(self, department):
        u = _make_scoped_user(department, 'g1_approve_only', ('recruit:candidate:offer:approve',))
        assert has_perm(u, 'recruit:candidate:offer:approve') is True
        assert has_perm(u, 'recruit:candidate:offer:edit') is False

    def test_edit_holder(self, department):
        u = _make_scoped_user(department, 'g1_edit_only', ('recruit:candidate:offer:edit',))
        assert has_perm(u, 'recruit:candidate:offer:edit') is True
        assert has_perm(u, 'recruit:candidate:offer:approve') is False


# ---------------------------------------------------------------------------
# demand transition HTTP 黑盒：审批码真实拦截
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDemandTransitionApprove:
    @pytest.fixture
    def process(self, db):
        """与 test_demand.py 同款最小流程（Demand.process NOT NULL）."""
        from apps.process.models import RecruitmentProcess, StageStatus
        return RecruitmentProcess.objects.create(
            id='proc-g1-001',
            code='G1_PROC',
            name='G1 测试流程',
            current_version='V1.0',
            is_template=False,
            is_enabled=True,
            is_latest=True,
            status=StageStatus.ENABLED,
        )

    @pytest.fixture
    def pending_demand(self, department, hr_user, process):
        data = DemandCreateData(
            title='G1 审批码回归',
            department_id=department.id,
            requested_by_id=hr_user.id,
            hr_id=hr_user.id,
            headcount=1,
            process_id=process.id,
            actor=hr_user,
        )
        demand = DemandService.create_demand(data)
        return DemandService.submit_for_approval(demand.id, hr_user)

    def test_edit_only_user_cannot_approve(self, pending_demand, department):
        """仅有 :edit 码的身份审批 → 403（修复前会放行）。"""
        u = _make_scoped_user(
            department, 'g1_dm_edit',
            ('recruit:demand:list', 'recruit:demand:edit'),
        )
        resp = _client_for(u).post(
            f'/api/v1/demands/{pending_demand.id}/transition/',
            {'action': 'approve'}, format='json',
        )
        assert resp.status_code == 403
        # django_fsm 禁止直接 setattr state，refresh_from_db 会炸，改重查
        assert Demand.objects.get(pk=pending_demand.pk).state == DemandState.PENDING

    def test_approve_only_user_can_approve(self, pending_demand, department):
        """仅有审批码的身份审批 → 通过权限层，状态流转成功（修复前 403）。"""
        u = _make_scoped_user(
            department, 'g1_dm_approve',
            ('recruit:demand:list', 'recruit:demand:approve'),
        )
        resp = _client_for(u).post(
            f'/api/v1/demands/{pending_demand.id}/transition/',
            {'action': 'approve'}, format='json',
        )
        assert resp.status_code == 200
        assert Demand.objects.get(pk=pending_demand.pk).state == DemandState.APPROVED

    def test_approve_only_user_cannot_nonapprove_transition(self, pending_demand, department):
        """仅有审批码的身份执行非审批动作（submit）→ 403（需 :edit）。"""
        u = _make_scoped_user(
            department, 'g1_dm_approve2',
            ('recruit:demand:list', 'recruit:demand:approve'),
        )
        resp = _client_for(u).post(
            f'/api/v1/demands/{pending_demand.id}/transition/',
            {'action': 'submit'}, format='json',
        )
        assert resp.status_code == 403
