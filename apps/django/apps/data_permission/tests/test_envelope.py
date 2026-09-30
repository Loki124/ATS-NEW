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
    resp = auth_client.patch(f'{LIST}{rule.id}/', {'priority': 5}, format='json')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['success'] is True
    rule.refresh_from_db()
    assert rule.priority == 5


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
