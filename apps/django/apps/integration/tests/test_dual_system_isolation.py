"""双系统(社会/校园招聘)数据隔离集成测试 (Phase 3).

硬证据目标: 证明 recruit_type 是系统级硬分区, 对所有用户(含超管)生效,
且写入侧由请求上下文权威注入, 不受客户端自填值影响.

覆盖:
- RecruitTypeMiddleware 请求头解析 (含缺省/非法回落)
- recruit_type_filter_q 纯函数 (硬分区 Q / no-op)
- scope_filter_q 对超管仍生效 recruit_type 分区
- ScopeQuerysetMixin.scope_queryset 读侧分区 (opt-in, 仅当模型有该字段)
- CandidateService.create_candidate 写侧权威注入 recruit_type
"""
from types import SimpleNamespace

import pytest
from django.db.models import Q
from django.test import RequestFactory

from apps.candidate.models import Candidate
from apps.candidate.services import CandidateService, CandidateCreateData
from apps.core.middleware import RecruitTypeMiddleware
from apps.core.permissions_v2 import ScopeQuerysetMixin
from apps.core.scope_resolver import recruit_type_filter_q, scope_filter_q
from apps.reason_library.models import RecruitType


def _superuser_stub():
    """is_super_admin 仅读 is_superuser + is_authenticated, 桩即可."""
    return SimpleNamespace(is_superuser=True, is_authenticated=True)


def _make_candidate(name, phone, recruit_type=RecruitType.SOCIAL.value):
    data = CandidateCreateData(name=name, phone=phone)
    return CandidateService.create_candidate(data, actor=None, recruit_type=recruit_type)


# ---------------------------------------------------------------------------
# 1. 中间件: 请求头解析
# ---------------------------------------------------------------------------
def test_middleware_parses_valid_header():
    rf = RequestFactory()
    mw = RecruitTypeMiddleware(lambda r: r)
    req = rf.get('/api/v1/candidates/', HTTP_X_RECRUIT_TYPE='campus')
    mw(req)
    assert req.recruit_type == 'campus'


def test_middleware_defaults_to_social_when_absent():
    rf = RequestFactory()
    mw = RecruitTypeMiddleware(lambda r: r)
    req = rf.get('/api/v1/candidates/')
    mw(req)
    assert req.recruit_type == 'social'


def test_middleware_rejects_illegal_value():
    rf = RequestFactory()
    mw = RecruitTypeMiddleware(lambda r: r)
    req = rf.get('/api/v1/candidates/', HTTP_X_RECRUIT_TYPE='bogus')
    mw(req)
    assert req.recruit_type == 'social'


# ---------------------------------------------------------------------------
# 2. 纯函数: 硬分区 Q
# ---------------------------------------------------------------------------
def test_recruit_type_filter_q_returns_partition():
    assert recruit_type_filter_q('campus') == Q(recruit_type='campus')
    assert recruit_type_filter_q('social') == Q(recruit_type='social')


def test_recruit_type_filter_q_noop_when_absent():
    assert recruit_type_filter_q(None) == Q()
    assert recruit_type_filter_q('') == Q()


# ---------------------------------------------------------------------------
# 3. scope_filter_q: 超管仍受 recruit_type 硬分区约束
# ---------------------------------------------------------------------------
def test_scope_filter_q_superuser_partition():
    admin = _superuser_stub()
    q_campus = scope_filter_q(admin, recruit_type='campus')
    q_social = scope_filter_q(admin, recruit_type='social')
    assert 'recruit_type' in str(q_campus) and 'campus' in str(q_campus)
    assert 'recruit_type' in str(q_social) and 'social' in str(q_social)
    # 未传 recruit_type -> no-op (不影响旧调用方)
    assert scope_filter_q(admin) == Q()


# ---------------------------------------------------------------------------
# 4. ScopeQuerysetMixin 读侧: 真实数据证明分区生效
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_mixin_scope_queryset_partitions_real_rows():
    # 写两条分属不同系统的候选人 (不经过分区, 直接落库以构造跨系统数据)
    social_c = _make_candidate('社招王', '13800138000', RecruitType.SOCIAL.value)
    campus_c = _make_candidate('校招李', '13900139000', RecruitType.CAMPUS.value)

    view = ScopeQuerysetMixin()
    view.request = SimpleNamespace(user=_superuser_stub(), recruit_type=RecruitType.CAMPUS.value)
    view.queryset = Candidate.objects.all()

    campus_qs = view.scope_queryset(Candidate.objects.all())
    ids = set(campus_qs.values_list('id', flat=True))
    assert campus_c.id in ids
    assert social_c.id not in ids

    # 切回 social 上下文 -> 仅社招可见
    view.request = SimpleNamespace(user=_superuser_stub(), recruit_type=RecruitType.SOCIAL.value)
    social_qs = view.scope_queryset(Candidate.objects.all())
    ids2 = set(social_qs.values_list('id', flat=True))
    assert social_c.id in ids2
    assert campus_c.id not in ids2


# ---------------------------------------------------------------------------
# 5. 写侧: CandidateService 由请求上下文权威注入 recruit_type
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_candidate_service_write_stamps_recruit_type():
    campus_c = _make_candidate('校招写入', '13700137000', RecruitType.CAMPUS.value)
    social_c = _make_candidate('社招写入', '13600136000', RecruitType.SOCIAL.value)
    assert campus_c.recruit_type == RecruitType.CAMPUS.value
    assert social_c.recruit_type == RecruitType.SOCIAL.value


@pytest.mark.django_db
def test_candidate_service_write_default_social():
    # 不显式传 recruit_type -> 默认 social (历史数据/未分区入口兜底)
    c = _make_candidate('默认写入', '13500135000')
    c.refresh_from_db()
    assert c.recruit_type == RecruitType.SOCIAL.value
