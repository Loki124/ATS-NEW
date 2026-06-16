"""Demand app 测试套件 (PRD v4 §14.1)"""
import pytest
from django.core.exceptions import ValidationError

from apps.demand.models import Demand, DemandApproval, DemandState
from apps.demand.services import DemandCreateData, DemandService
from apps.process.models import RecruitmentProcess, StageStatus, StageType


@pytest.fixture
def process(db):
    return RecruitmentProcess.objects.create(
        id='proc-test-001',
        code='TEST_PROC',
        name='测试流程',
        current_version='V1.0',
        is_template=False,
        is_enabled=True,
        status=StageStatus.ENABLED,
    )


@pytest.fixture
def process_stage(db, process):
    from apps.process.models import RecruitmentStage
    return RecruitmentStage.objects.create(
        id='stage-test-001',
        code='TEST_STAGE',
        name='测试阶段',
        stage_type=StageType.FILTER,
        status=StageStatus.ENABLED,
        is_builtin=False,
    )


@pytest.mark.django_db
class TestDemandService:
    def test_create_demand(self, department, hr_user, hrbp_user, process):
        data = DemandCreateData(
            title='招聘 Python 工程师',
            department_id=department.id,
            requested_by_id=hr_user.id,
            hr_id=hrbp_user.id,
            headcount=2,
            process_id=process.id,
            jd='负责后端开发',
            requirements='3 年以上 Python 经验',
            priority='P1',
            actor=hr_user,
        )
        demand = DemandService.create_demand(data)
        assert demand.id is not None
        assert demand.state == DemandState.DRAFT
        assert demand.code.startswith('D')
        assert demand.headcount == 2

    def test_submit_for_approval(self, department, hr_user, hrbp_user, process):
        data = DemandCreateData(
            title='Java 开发',
            department_id=department.id,
            requested_by_id=hr_user.id,
            hr_id=hrbp_user.id,
            headcount=1,
            process_id=process.id,
            actor=hr_user,
        )
        demand = DemandService.create_demand(data)
        submitted = DemandService.submit_for_approval(demand.id, hr_user)
        assert submitted.state == DemandState.PENDING
        assert demand.approvals.count() == 1

    def test_approve_flow(self, department, hr_user, hrbp_user, process):
        data = DemandCreateData(
            title='Go 工程师',
            department_id=department.id,
            requested_by_id=hr_user.id,
            hr_id=hrbp_user.id,
            headcount=1,
            process_id=process.id,
            actor=hr_user,
        )
        demand = DemandService.create_demand(data)
        DemandService.submit_for_approval(demand.id, hr_user)
        approved = DemandService.approve(demand.id, hrbp_user.id, '同意')
        assert approved.state == DemandState.APPROVED

    def test_reject_flow(self, department, hr_user, hrbp_user, process):
        data = DemandCreateData(
            title='PHP 工程师',
            department_id=department.id,
            requested_by_id=hr_user.id,
            hr_id=hrbp_user.id,
            headcount=1,
            process_id=process.id,
            actor=hr_user,
        )
        demand = DemandService.create_demand(data)
        DemandService.submit_for_approval(demand.id, hr_user)
        rejected = DemandService.reject(demand.id, hrbp_user.id, '需求不清晰')
        assert rejected.state == DemandState.REJECTED

    def test_cancel(self, department, hr_user, hrbp_user, process):
        data = DemandCreateData(
            title='取消测试',
            department_id=department.id,
            requested_by_id=hr_user.id,
            hr_id=hrbp_user.id,
            headcount=1,
            process_id=process.id,
            actor=hr_user,
        )
        demand = DemandService.create_demand(data)
        cancelled = DemandService.cancel(demand.id, '招聘冻结', hrbp_user)
        assert cancelled.state == DemandState.CANCELLED


@pytest.mark.django_db
class TestDemandAPI:
    def test_list_demands(self, auth_hr_client):
        response = auth_hr_client.get('/api/v1/demands/')
        assert response.status_code == 200
        assert response.data['success'] is True
        assert 'data' in response.data

    def test_unauth_list_demands(self, api_client):
        response = api_client.get('/api/v1/demands/')
        assert response.status_code == 401

    def test_demand_state_filter(self, auth_hr_client, department, hr_user, hrbp_user, process):
        from apps.demand.services import DemandCreateData, DemandService
        data = DemandCreateData(
            title='待审批需求',
            department_id=department.id,
            requested_by_id=hr_user.id,
            hr_id=hrbp_user.id,
            headcount=1,
            process_id=process.id,
            actor=hr_user,
        )
        demand = DemandService.create_demand(data)
        DemandService.submit_for_approval(demand.id, hr_user)
        response = auth_hr_client.get('/api/v1/demands/?state=PENDING')
        assert response.status_code == 200
        # 验证过滤生效
        codes = [d['code'] for d in response.data['data']['results']]
        assert demand.code in codes
