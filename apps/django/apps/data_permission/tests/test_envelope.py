"""信封契约 — DataPermissionRuleViewSet (信封收口 Batch 3).

list 已由 StandardResultsSetPagination 包 {success, data}; options 自定义动作自带信封.
本测试只验证经 EnvelopeWriteMixin 兜底的 create / retrieve / update.
仅超管可写, 用 super_user(auth_client) 通过 IsSuperAdmin 闸门.
"""
import pytest
from rest_framework import status

from apps.data_permission.models import DataPermissionRule

LIST = '/api/v1/data-permissions/'


@pytest.fixture
def rule(db):
    return DataPermissionRule.objects.create(
        dimension_type='ROLE',
        dimension_value='hrbp',
        level='ROW',
    )


def test_data_permission_rule_retrieve_envelope(auth_client, rule):
    resp = auth_client.get(f'{LIST}{rule.id}/')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['success'] is True
    assert 'data' in resp.data


def test_data_permission_rule_update_envelope(auth_client, rule):
    """PATCH 仍可用（信封 + 部分更新语义）。

    2026-10-14: 原用例PATCH 的是 `priority` 字段，该字段已随T01 下掉，
    故改为PATCH `remark` —— 保留"部分更新走 EnvelopeWriteMixin 且返回信封"
    这一真正被测的契约。
    """
    resp = auth_client.patch(f'{LIST}{rule.id}/', {'remark': 'x'}, format='json')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['success'] is True
    rule.refresh_from_db()
    assert rule.remark == 'x'


def test_priority_field_is_gone_and_patch_is_ignored(auth_client, rule):
    """下掉 priority 后该字段必须**不存在**，且 PATCH 它不得 500。

    DRF 的 ModelSerializer 会静默忽略未声明的字段，因此 PATCH {"priority": 5}
    应当被忽略（200）而不是崩 500 —— 这是 DR-04b 要求同步从序列化器移除的原因：
    若只删模型字段而保留在 `fields` 里，PATCH 该字段会变成 500 或静默漂移。
    """
    resp = auth_client.patch(f'{LIST}{rule.id}/', {'priority': 5}, format='json')
    assert resp.status_code == status.HTTP_200_OK
    rule.refresh_from_db()
    assert not hasattr(rule, 'priority')
    # 序列化输出里也不应再出现该字段（前后端契约同步下掉）
    assert 'priority' not in resp.data['data']


def test_data_permission_rule_create_envelope(auth_client):
    payload = {
        'dimension_type': 'ROLE',
        'dimension_value': 'super_admin_x',
        'level': 'ROW',
    }
    resp = auth_client.post(LIST, payload, format='json')
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data['success'] is True
    assert 'data' in resp.data
    assert DataPermissionRule.objects.filter(dimension_value='super_admin_x').exists()
