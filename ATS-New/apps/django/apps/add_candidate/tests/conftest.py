"""Add Candidate V2 - 共享 pytest fixtures

注意：
- hr_user / super_user / department / hr_role 等通用 fixture 由顶层 tests/conftest.py 提供
  （pytest 自动发现所有 conftest.py），本文件**不**重定义，避免 fixture name shadowing。
- 本文件只定义 add_candidate 专用的 fixture：process / published_position / clean_candidate
"""
import pytest
from apps.candidate.models import Candidate, CandidateState
from apps.process.models import RecruitmentProcess, StageStatus


@pytest.fixture
def process(db):
    """add_candidate 测试用的招聘流程"""
    return RecruitmentProcess.objects.create(
        id='proc-add-candidate-test',
        code='ADD_CANDIDATE_TEST',
        name='Add Candidate 测试流程',
        current_version='V1.0',
        is_template=False,
        is_enabled=True,
        status=StageStatus.ENABLED,
    )


@pytest.fixture
def published_position(db, department, hr_user, process):
    """可投递的职位（state=RECRUITING）

    链路：DRAFT → submit_publish() → PENDING_PUBLISH → publish() → PUBLISHED → start_recruiting() → RECRUITING
    """
    from apps.position.models import Position, PositionState
    pos = Position.objects.create(
        id='pos-add-candidate-test',
        code='P_ADD_CANDIDATE_TEST',
        title='高级前端工程师',
        description='负责核心产品前端开发',
        department=department,
        hiring_manager=hr_user,
        owner=hr_user,
        headcount=1,
        filled_count=0,
        state=PositionState.DRAFT,
        process=process,
    )
    pos.submit_publish()
    pos.save()
    pos.publish()
    pos.save()
    pos.start_recruiting()
    pos.save()
    return pos


@pytest.fixture
def clean_candidate(db):
    """无重复的候选人"""
    return Candidate.objects.create(
        id='cand-clean-test-001',
        name='张三',
        phone='13800138001',
        email='zhang@test.com',
        current_state=CandidateState.APPLIED,
    )
