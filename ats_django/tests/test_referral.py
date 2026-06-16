"""Referral app 测试 (PRD v4 §6.4 N+1/N+2)"""
import pytest

from apps.process.models import RecruitmentProcess, StageStatus
from apps.referral.models import Referral, ReferralType
from apps.referral.services import ReferralCreateData, ReferralService


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
def candidate(db):
    from apps.candidate.models import Candidate
    return Candidate.objects.create(
        id='cand-test-001',
        name='测试候选人',
        phone='13800000001',
        email='test@example.com',
    )


@pytest.fixture
def same_dept_position(db, department, hrbp_user, process):
    from apps.position.models import Position, PositionState
    return Position.objects.create(
        id='pos-test-001',
        code='P_TEST',
        title='同部门测试职位',
        department=department,
        hiring_manager=hrbp_user,
        owner=hrbp_user,
        headcount=1,
        filled_count=0,
        state=PositionState.DRAFT,
        process=process,
    )


@pytest.mark.django_db
class TestReferralN1Detection:
    def test_same_department_is_n_plus_1(self, hrbp_user, candidate, same_dept_position):
        data = ReferralCreateData(
            referrer_id=hrbp_user.id,
            candidate_id=candidate.id,
            position_id=same_dept_position.id,
            referral_type=ReferralType.INTERNAL,
            actor=hrbp_user,
        )
        referral = ReferralService.create_referral(data)
        assert referral.detected_type == ReferralType.N_PLUS_1
        assert referral.status == 'SUBMITTED'

    def test_social_when_no_match(self, hrbp_user, candidate, db, process):
        from apps.position.models import Position, PositionState
        from apps.core.models import Department
        other_dept = Department.objects.create(id='dept-other', name='其他部门', code='OTHER_DEPT')
        pos = Position.objects.create(
            id='pos-other-001', code='P_OTHER', title='其他部门职位',
            department=other_dept, hiring_manager=hrbp_user, owner=hrbp_user,
            headcount=1, state=PositionState.DRAFT, process=process,
        )
        data = ReferralCreateData(
            referrer_id=hrbp_user.id, candidate_id=candidate.id, position_id=pos.id,
            referral_type=ReferralType.SOCIAL, actor=hrbp_user,
        )
        referral = ReferralService.create_referral(data)
        assert referral.detected_type == ReferralType.SOCIAL


@pytest.mark.django_db
class TestReferralAPI:
    def test_list_referrals(self, auth_hr_client, hrbp_user, candidate, same_dept_position):
        data = ReferralCreateData(
            referrer_id=hrbp_user.id, candidate_id=candidate.id,
            position_id=same_dept_position.id,
            referral_type=ReferralType.INTERNAL, actor=hrbp_user,
        )
        ReferralService.create_referral(data)
        response = auth_hr_client.get('/api/v1/referrals/')
        assert response.status_code == 200
        assert response.data['success'] is True
