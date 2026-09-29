"""G42 系统锁定字段(编号/名称/状态)细粒度编辑守卫测试 (2026-09-27 修正)。

修复前: 锁定字段(需求编号/名称/状态)整体编辑被 400 拦截, 连 label 都不让改。
修复后: 锁定字段仅「字段类型(field_type)」与「停用状态(status: active/inactive)」
        两项不可改, 其余所有属性(label/英文/提示/必填/可见/选项/分组/排序/可见权限等)
        放行; 非锁定系统字段改 field_type 等结构性属性照常允许(回归)。

请求体统一 camelCase, 与真实前端一致 (全局 CamelCaseJSONParser 负责转换)。
"""
import pytest
from rest_framework.test import APIClient

from apps.dynamic_field.models import DynamicField

RESOURCE = 'Demand'
LIST_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/'


def detail_url(lookup: str) -> str:
    """detail 端点 URL (lookup 正常应为 DynamicField.id)。"""
    return f'/api/v1/dynamic-fields/{RESOURCE}/fields/{lookup}/'


@pytest.fixture
def client(hr_user) -> APIClient:
    """已认证的 API client (视图只要求 IsAuthenticated)。"""
    api_client = APIClient()
    api_client.force_authenticate(user=hr_user)
    return api_client


@pytest.fixture
def locked_field(db) -> DynamicField:
    """锁定核心标识字段(需求编号, field_key=code, 属 SYSTEM_FIELD_LOCKED_KEYS)。

    复用 0019 种子已落成的 (Demand, code) 系统字段行, 覆盖测试关心的属性,
    避免与种子迁移撞唯一键 (resource, field_key)。
    """
    return DynamicField.objects.update_or_create(
        resource=RESOURCE, field_key='code',
        defaults=dict(
            label='需求编号',
            field_type=DynamicField.FieldType.TEXT, status='active',
            is_system=True, is_required=True, order_index=10,
        ),
    )[0]


@pytest.fixture
def non_locked_system_field(db) -> DynamicField:
    """非锁定系统字段(负责HR, field_key=hr, 不在 LOCKED 集合, 可改结构性属性)。

    复用 0019 种子已落成的 (Demand, hr) 系统字段行, 覆盖测试关心的属性,
    避免与种子迁移撞唯一键 (resource, field_key)。
    """
    return DynamicField.objects.update_or_create(
        resource=RESOURCE, field_key='hr',
        defaults=dict(
            label='负责HR',
            field_type=DynamicField.FieldType.TEXT, status='active',
            is_system=True, order_index=100,
        ),
    )[0]


@pytest.mark.django_db
class TestLockedFieldEdit:
    """锁定字段(需求编号)细粒度守卫。"""

    def test_locked_field_update_label_returns_200(self, client, locked_field):
        """改 label → 200 且落库生效 (用户要求其余属性均可编辑)。"""
        resp = client.patch(detail_url(locked_field.id), {'label': '需求编号X'}, format='json')
        assert resp.status_code == 200, resp.content
        locked_field.refresh_from_db()
        assert locked_field.label == '需求编号X'

    def test_locked_field_update_placeholder_visible_required_200(self, client, locked_field):
        """改非受限属性(占位提示/必填/可见)组合 → 200。"""
        resp = client.patch(detail_url(locked_field.id), {
            'placeholder': '请输入编号', 'isRequired': False, 'isVisible': True,
        }, format='json')
        assert resp.status_code == 200, resp.content
        locked_field.refresh_from_db()
        assert locked_field.placeholder == '请输入编号'
        assert locked_field.is_required is False

    def test_locked_field_change_field_type_returns_400(self, client, locked_field):
        """改 field_type → 400 (锁定项之一)。"""
        resp = client.put(
            detail_url(locked_field.id),
            {'fieldKey': 'code', 'label': '需求编号', 'fieldType': 'NUMBER'},
            format='json',
        )
        assert resp.status_code == 400, resp.content
        body = resp.json()
        assert '字段类型' in body['errors']['detail']

    def test_locked_field_same_field_type_ok(self, client, locked_field):
        """携带与现值相同的 field_type 不算"修改", 不触发 400。"""
        resp = client.put(
            detail_url(locked_field.id),
            {'fieldKey': 'code', 'label': '需求编号', 'fieldType': 'TEXT'},
            format='json',
        )
        assert resp.status_code == 200, resp.content

    def test_locked_field_change_status_returns_400(self, client, locked_field):
        """改停用状态(status) → 400 (锁定项之二)。"""
        resp = client.patch(detail_url(locked_field.id), {'status': 'inactive'}, format='json')
        assert resp.status_code == 400, resp.content
        body = resp.json()
        assert '停用' in body['errors']['detail'] or '启用' in body['errors']['detail']

    def test_locked_field_identity_key_protected(self, client, locked_field):
        """改 field_key(身份键)被强制回注, 保持原值, 不报错。"""
        resp = client.patch(
            detail_url(locked_field.id),
            {'fieldKey': 'code_renamed', 'label': '需求编号'},
            format='json',
        )
        assert resp.status_code == 200, resp.content
        locked_field.refresh_from_db()
        assert locked_field.field_key == 'code'


@pytest.mark.django_db
class TestNonLockedSystemFieldEditRegression:
    """非锁定系统字段结构性属性放行(回归)。"""

    def test_non_locked_system_field_change_field_type_returns_200(self, client, non_locked_system_field):
        """非锁定系统字段改 field_type → 200 (结构性属性放行)。"""
        resp = client.put(
            detail_url(non_locked_system_field.id),
            {'fieldKey': 'hr', 'label': '负责HR', 'fieldType': 'NUMBER'},
            format='json',
        )
        assert resp.status_code == 200, resp.content
        non_locked_system_field.refresh_from_db()
        assert non_locked_system_field.field_type == 'NUMBER'

    def test_non_locked_system_field_change_status_returns_200(self, client, non_locked_system_field):
        """非锁定系统字段改停用状态 → 200 (仅锁定字段禁用停用)。"""
        resp = client.patch(detail_url(non_locked_system_field.id), {'status': 'inactive'}, format='json')
        assert resp.status_code == 200, resp.content
        non_locked_system_field.refresh_from_db()
        assert non_locked_system_field.status == 'inactive'
