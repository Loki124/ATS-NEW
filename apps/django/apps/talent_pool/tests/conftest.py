"""Talent Pool 测试共享 fixtures

`clean_candidate` 在 add_candidate 专属 conftest 中定义（依赖不同的模型字段）。
本测试不依赖 add_candidate 的 process/position 链，只复用 Candidate 创建逻辑。
"""
# 2026-08-03 R7：`pytest_plugins = ['tests.conftest']` 已上提到 rootdir 顶层
# conftest（apps/django/conftest.py）；pytest 8+ 禁止在非顶层 conftest 声明。
import pytest
from apps.candidate.models import Candidate, CandidateState


@pytest.fixture
def clean_candidate(db):
    """无重复的候选人"""
    return Candidate.objects.create(
        id='cand-talent-pool-test-001',
        name='张三',
        phone='13800138002',
        email='zhang.tp@test.com',
        current_state=CandidateState.APPLIED,
    )