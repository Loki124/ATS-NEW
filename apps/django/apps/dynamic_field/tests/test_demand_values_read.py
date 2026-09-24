"""动态字段值「按实体读取」端点回归测试 (2026-09-24 兵哥)。

需求 4: 需求详情页要按 (resource, entity_id) 读取 DynamicFieldValue 来渲染
「模型映射字段之外的扩展字段」。GET /dynamic-fields/<resource>/fields/values/?entity_id=X
返回 { data: [{ fieldKey, value }] } (数组 + 字符串 fieldKey, 避免全局 CamelCaseJSONRenderer
把 dict 的 snake 键 camel 化后与 listFields 的 snake fieldKey 错位)。本测试覆盖该读取契约与空值边界。
"""
import pytest
from rest_framework.test import APIClient

from apps.dynamic_field.models import DynamicField, DynamicFieldValue

RESOURCE = 'Demand'
VALUES_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/values/'


@pytest.fixture
def client(hr_user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(user=hr_user)
    return api_client


@pytest.fixture
def custom_field(db) -> DynamicField:
    return DynamicField.objects.create(
        resource=RESOURCE,
        field_key='f_custom_text',
        label='自定义文本',
        field_type=DynamicField.FieldType.TEXT,
        order_index=0,
    )


@pytest.mark.django_db
class TestReadValuesByEntity:
    """GET /dynamic-fields/<resource>/fields/values/?entity_id=X"""

    def test_read_returns_stored_values(self, client, custom_field):
        DynamicFieldValue.objects.create(
            resource=RESOURCE, entity_id='demand-1',
            field_key='f_custom_text', value='hello',
        )
        resp = client.get(VALUES_URL, {'entity_id': 'demand-1'})
        assert resp.status_code == 200, resp.content
        # 返回数组, fieldKey 保持原始 snake (f_custom_text), 与前端 listFields 的 fieldKey 对齐。
        assert resp.json()['data'] == [{'fieldKey': 'f_custom_text', 'value': 'hello'}]

    def test_read_missing_entity_id_returns_empty(self, client):
        resp = client.get(VALUES_URL)
        assert resp.status_code == 200, resp.content
        assert resp.json()['data'] == []

    def test_read_ignores_other_resources(self, client, custom_field):
        # 同 entity_id 但不同 resource 的值不应串读
        DynamicFieldValue.objects.create(
            resource='Candidate', entity_id='demand-1',
            field_key='f_custom_text', value='leak',
        )
        resp = client.get(VALUES_URL, {'entity_id': 'demand-1'})
        assert resp.json()['data'] == []
