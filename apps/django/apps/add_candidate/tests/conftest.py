"""Add Candidate V2 - 共享 pytest fixtures

注意：
- hr_user / super_user / department / hr_role 等通用 fixture 由顶层 tests/conftest.py 提供
  （pytest 自动发现所有 conftest.py），本文件**不**重定义，避免 fixture name shadowing。
- 本文件只定义 add_candidate 专用的 fixture：process / published_position / clean_candidate
"""
# 2026-08-03 R7：`pytest_plugins = ['tests.conftest']` 已上提到 rootdir 顶层
# conftest（apps/django/conftest.py）。pytest 8+ 禁止在非顶层 conftest 声明
# pytest_plugins（它实际作用于全量测试而非本目录，语义有误导性），保留会让
# `testpaths = tests apps` 在收集阶段直接报错。
import pytest
from apps.candidate.models import Candidate, CandidateState
from apps.process.models import RecruitmentProcess


@pytest.fixture
def process(db):
    """add_candidate 测试用的招聘流程"""
    return RecruitmentProcess.objects.create(
        id='proc-add-candidate-test',
        code='ADD_CANDIDATE_TEST',
        name='Add Candidate 测试流程',
        current_version='1.0',  # 与 Position.process_version 默认值一致（显式传值，不受模型 default 变更影响）
        is_template=False,
        is_enabled=True,
        is_latest=True,  # T1：is_latest 默认 False，依赖 is_latest=True 过滤的查询会落空
        # status 字段默认 'ENABLED'，无需显式传
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


@pytest.fixture
def candidate_with_active_app(db, published_position):
    """已有 active application 的候选人（用于测试 occupied 状态）"""
    from apps.candidate.models import Candidate
    from apps.application.models import Application, ApplicationState
    cand = Candidate.objects.create(name='重复测试', phone='13911111111')
    Application.objects.create(
        candidate=cand,
        position=published_position,
        process=published_position.process,
        workflow_version=published_position.process.current_version,
        code='APP-DUP-001',
        state=ApplicationState.ACTIVE,
    )
    return cand
