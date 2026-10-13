"""回归：候选人 state_display 出参（BUG 修复 2026-10-13）。

根因：``current_state`` 是 ``FSMField`` 且未声明 ``choices``，Django 不会自动生成
``get_<field>_display``；而 List/Detail 两个序列化器的 ``state_display`` 均以
``source='get_current_state_display'`` 取值，缺该方法时解析抛 AttributeError，
被 ``FieldAclSerializerMixin`` 静默丢弃 → 前端候选人详情「当前阶段/状态」恒空。

修复：模型显式新增 ``get_current_state_display()``，从 ``CandidateState`` 枚举取 label。
"""
import pytest

from apps.candidate.models import Candidate, CandidateState
from apps.candidate.serializers import CandidateDetailSerializer


@pytest.mark.django_db
def test_get_current_state_display_maps_every_state():
    """全枚举：每个 current_state 都能取到中文 label（修复前一律 AttributeError）。"""
    for state in CandidateState:
        c = Candidate(name='状态展示', phone='13800000001')
        c.__dict__['current_state'] = state.value  # 绕过 FSMField 描述符
        assert c.get_current_state_display() == state.label


@pytest.mark.django_db
def test_get_current_state_display_invalid_fallback():
    """非法状态值不回抛，原样回退（fail-soft，避免序列化 500）。"""
    c = Candidate(name='异常态', phone='13800000002')
    c.__dict__['current_state'] = 'NOT_A_STATE'
    assert c.get_current_state_display() == 'NOT_A_STATE'


@pytest.mark.django_db
def test_detail_serializer_includes_state_display():
    """关键断言：Detail 序列化器出参必须含 state_display 且值正确（修复前该键被丢弃）。"""
    c = Candidate.objects.create(name='序列化', phone='13800000003')
    data = CandidateDetailSerializer(c).data
    assert 'state_display' in data, 'state_display 被静默丢弃 → 前端拿不到流程阶段'
    assert data['state_display'] == CandidateState.APPLIED.label == '已投递'
