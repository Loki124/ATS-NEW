"""统一规则只读 API 测试（Phase 1）。

用 DRF APIClient 测三端点 200 + 结构。rules 列表对 aggregate_rules 打 monkey-patch，
避免依赖完整 legacy DB fixture。注意：CamelCaseJSONRenderer 全局启用，出参为驼峰键。
"""
import pytest
from rest_framework.test import APIClient

from apps.rule_engine.adapters import UnifiedRuleDTO
from apps.rule_engine.models import RuleCategory, UnifiedActionType, UnifiedOperator, UnifiedTriggerType

# 复用全局 auth_client fixture（tests/fixtures_common，基于 JWT 认证的 super_user）；
# 本模块不再自定义，避免裸用户被 IsAuthenticatedDenyByDefault 拒绝(403)。
pytestmark = pytest.mark.django_db


@pytest.fixture
def fixed_dto():
    return UnifiedRuleDTO(
        id='x1', name='测试规则', category=RuleCategory.TCA, source_app='automation',
        trigger_type=UnifiedTriggerType.STAGE_ENTERED,
        legacy_model='apps.automation.AutomationRule', legacy_id='x1',
        actions_summary=[{'seq': 1, 'action_type': UnifiedActionType.ALLOW, 'params': {}}],
        conditions_summary=[{'seq': 1, 'condition_type': 'CUSTOM', 'field': 'age',
                             'operator': 'GT', 'value': 18}],
    )


def test_rules_list(auth_client, fixed_dto, monkeypatch):
    monkeypatch.setattr('apps.rule_engine.views.aggregate_rules', lambda filters=None: [fixed_dto])
    resp = auth_client.get('/api/v1/rule-engine/rules/')
    assert resp.status_code == 200
    body = resp.data  # DRF 解析后的内容（序列化层为 snake_case；camelCase 仅发生在最终 JSON 渲染）
    assert body['success'] is True
    assert isinstance(body['data'], list)
    assert body['data'][0]['source_app'] == 'automation'
    assert body['data'][0]['category'] == RuleCategory.TCA
    assert body['data'][0]['legacy_model'] == 'apps.automation.AutomationRule'
    assert body['data'][0]['conditions_summary'][0]['field'] == 'age'
    assert 'pagination' in body


def test_rules_list_filter_query_param(auth_client, fixed_dto, monkeypatch):
    # 验证视图把 query_params 透传给 aggregate_rules
    captured = {}

    def fake_aggregate(filters=None):
        captured.update(filters or {})
        return [fixed_dto]

    monkeypatch.setattr('apps.rule_engine.views.aggregate_rules', fake_aggregate)
    resp = auth_client.get('/api/v1/rule-engine/rules/?source_app=automation&category=TCA')
    assert resp.status_code == 200
    assert captured.get('source_app') == 'automation'
    assert captured.get('category') == RuleCategory.TCA


def test_triggers_catalog(auth_client):
    resp = auth_client.get('/api/v1/rule-engine/triggers/')
    assert resp.status_code == 200
    vals = [item['value'] for item in resp.data]
    assert len(resp.data) == len(UnifiedTriggerType.choices)
    assert UnifiedTriggerType.STAGE_ENTERED in vals
    assert UnifiedTriggerType.BUSINESS_EVENT in vals


def test_operators_catalog(auth_client):
    resp = auth_client.get('/api/v1/rule-engine/operators/')
    assert resp.status_code == 200
    vals = [item['value'] for item in resp.data]
    assert len(resp.data) == len(UnifiedOperator.choices)
    assert 'BETWEEN' in vals
    assert 'IS_EMPTY' in vals


def test_rules_list_requires_auth():
    client = APIClient()
    resp = client.get('/api/v1/rule-engine/rules/')
    # 未认证 → 401（确认端点受全局认证保护，非裸奔）
    assert resp.status_code == 401
