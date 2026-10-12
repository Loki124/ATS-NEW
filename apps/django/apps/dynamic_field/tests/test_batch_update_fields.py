"""批量修改字段定义 (batch-update) 端点测试 (2026-10-12)。

覆盖「所有字段管理 → 批量操作」的后端契约:
  - 批量改字段类型(fieldType): 普通字段生效; 系统锁定字段(编号/名称/状态)逐条跳过;
    非锁定系统字段放行; 目标值即现值时视为已生效(不写库);
    改为非选项类型时清空手动 options (与单字段编辑一致);
    改为组合字段但缺子字段 → 单条 failed, 不影响其余条目;
  - 批量改字段分组(groupId): group_name 同步 + module_id 跟随分组所属模块;
    传 null = 移到未分组; 跨资源/已删除分组 → 整体 400;
  - 参数校验: 空 ids / 未指定任何属性 / 非法字段类型 / 超量 → 400;
  - 未知 id → skipped; ids 去重; 两项属性可同时生效。

请求体统一 camelCase, 与真实前端一致 (全局 CamelCaseJSONParser 负责转换)。
"""
import pytest
from rest_framework.test import APIClient

from apps.dynamic_field.models import DynamicField, FieldGroup, FieldModule

RESOURCE = 'Candidate'
BATCH_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/batch-update/'


@pytest.fixture
def client(hr_user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(user=hr_user)
    return api_client


@pytest.fixture
def module(db) -> FieldModule:
    return FieldModule.objects.create(resource=RESOURCE, code='batch_mod', name='批量模块', order_index=10)


@pytest.fixture
def group_a(module) -> FieldGroup:
    return FieldGroup.objects.create(module=module, code='batch_a', name='分组A', order_index=10)


@pytest.fixture
def group_b(module) -> FieldGroup:
    return FieldGroup.objects.create(module=module, code='batch_b', name='分组B', order_index=20)


@pytest.fixture
def plain_field(db) -> DynamicField:
    """普通自定义字段(无模块/分组)。"""
    return DynamicField.objects.create(
        resource=RESOURCE, field_key='batch_plain', label='普通字段',
        field_type=DynamicField.FieldType.TEXT, order_index=10,
    )


@pytest.fixture
def locked_field(db) -> DynamicField:
    """系统锁定字段(field_key=code, 属 SYSTEM_FIELD_LOCKED_KEYS): 字段类型不可改。"""
    return DynamicField.objects.create(
        resource=RESOURCE, field_key='code', label='编号',
        field_type=DynamicField.FieldType.TEXT, is_system=True, order_index=20,
    )


@pytest.fixture
def system_field(db) -> DynamicField:
    """非锁定系统字段: 结构性属性(含字段类型)放行。"""
    return DynamicField.objects.create(
        resource=RESOURCE, field_key='batch_sys', label='系统字段',
        field_type=DynamicField.FieldType.TEXT, is_system=True, order_index=30,
    )


@pytest.fixture
def option_field(db) -> DynamicField:
    """带手动选项的下拉字段。"""
    return DynamicField.objects.create(
        resource=RESOURCE, field_key='batch_opt', label='下拉字段',
        field_type=DynamicField.FieldType.SELECT, order_index=40,
        options=[{'value': 'a', 'label': '选项A'}],
    )


def _data(resp) -> dict:
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body['success'] is True
    return body['data']


# --- 字段类型 ---------------------------------------------------------------


@pytest.mark.django_db
class TestBatchFieldType:
    def test_updates_plain_and_non_locked_system_fields(self, client, plain_field, system_field):
        """普通字段 + 非锁定系统字段 → 全部生效。"""
        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id, system_field.id], 'fieldType': 'NUMBER',
        }, format='json', HTTP_HOST='localhost'))

        assert data['updatedCount'] == 2
        assert set(data['updated']) == {plain_field.id, system_field.id}
        assert data['skipped'] == [] and data['failed'] == []
        plain_field.refresh_from_db()
        system_field.refresh_from_db()
        assert plain_field.field_type == 'NUMBER'
        assert system_field.field_type == 'NUMBER'

    def test_skips_locked_system_field_with_reason(self, client, plain_field, locked_field):
        """锁定字段(编号)改类型 → 跳过并说明原因, 库里类型不变。"""
        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id, locked_field.id], 'fieldType': 'NUMBER',
        }, format='json', HTTP_HOST='localhost'))

        assert data['updatedCount'] == 1
        assert data['updated'] == [plain_field.id]
        assert len(data['skipped']) == 1
        assert data['skipped'][0]['id'] == locked_field.id
        assert '字段类型不可修改' in data['skipped'][0]['reason']
        locked_field.refresh_from_db()
        assert locked_field.field_type == 'TEXT'

    def test_same_type_is_noop_success(self, client, plain_field):
        """目标类型即现值 → 不写库, 计入成功(目标态已达成)。"""
        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id], 'fieldType': 'TEXT',
        }, format='json', HTTP_HOST='localhost'))
        assert data['updatedCount'] == 1
        assert data['skipped'] == [] and data['failed'] == []

    def test_clears_options_when_new_type_not_option_type(self, client, option_field):
        """下拉 → 文本: 手动 options 清空, 不残留脏数据。"""
        data = _data(client.post(BATCH_URL, {
            'ids': [option_field.id], 'fieldType': 'TEXT',
        }, format='json', HTTP_HOST='localhost'))
        assert data['updatedCount'] == 1
        option_field.refresh_from_db()
        assert option_field.field_type == 'TEXT'
        assert option_field.options == []

    def test_composite_without_subfields_fails_single(self, client, plain_field, system_field):
        """改为组合字段但缺子字段 → 该条 failed(附原因), 不影响其余条目。"""
        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id, system_field.id], 'fieldType': 'COMPOSITE',
        }, format='json', HTTP_HOST='localhost'))

        assert data['updatedCount'] == 0
        assert len(data['failed']) == 2
        assert all('子字段' in f['reason'] for f in data['failed'])
        plain_field.refresh_from_db()
        assert plain_field.field_type == 'TEXT'


# --- 字段分组 ---------------------------------------------------------------


@pytest.mark.django_db
class TestBatchGroup:
    def test_group_change_syncs_group_name_and_module(self, client, plain_field, group_b):
        """移组: group_id 生效 + group_name 同步 + module_id 跟随分组所属模块。"""
        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id], 'groupId': group_b.id,
        }, format='json', HTTP_HOST='localhost'))

        assert data['updatedCount'] == 1
        plain_field.refresh_from_db()
        assert plain_field.group_id == group_b.id
        assert plain_field.group_name == group_b.name
        assert plain_field.module_id == group_b.module_id

    def test_group_clear_moves_to_ungrouped(self, client, plain_field, group_a):
        """groupId 传 null → 移到未分组, group_name 一并清空, 模块保留。"""
        plain_field.group = group_a
        plain_field.group_name = group_a.name
        plain_field.save(update_fields=['group', 'group_name'])

        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id], 'groupId': None,
        }, format='json', HTTP_HOST='localhost'))

        assert data['updatedCount'] == 1
        plain_field.refresh_from_db()
        assert plain_field.group_id is None
        assert plain_field.group_name == ''

    def test_same_group_is_noop_success(self, client, plain_field, group_a):
        """目标分组即现分组 → 不写库, 计入成功。"""
        plain_field.group = group_a
        plain_field.group_name = group_a.name
        plain_field.save(update_fields=['group', 'group_name'])

        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id], 'groupId': group_a.id,
        }, format='json', HTTP_HOST='localhost'))
        assert data['updatedCount'] == 1
        assert data['failed'] == []

    def test_foreign_resource_group_returns_400(self, client, plain_field):
        """目标分组不属于当前资源 → 整体 400 (共享目标, 不必逐条试错)。"""
        other_module = FieldModule.objects.create(resource='Demand', code='batch_demand', name='需求模块')
        other_group = FieldGroup.objects.create(module=other_module, code='batch_dg', name='需求分组')

        resp = client.post(BATCH_URL, {
            'ids': [plain_field.id], 'groupId': other_group.id,
        }, format='json', HTTP_HOST='localhost')
        assert resp.status_code == 400, resp.content
        assert '不属于当前资源' in resp.json()['message']

    def test_deleted_group_returns_400(self, client, plain_field, group_a):
        """目标分组已软删 → 400。

        注意: Django ``delete()`` 会把实例 pk 置 None, 必须先取 id 再删,
        否则等于传 ``groupId=None``(移到未分组), 测不到校验分支。
        """
        group_id = group_a.id
        group_a.delete()
        resp = client.post(BATCH_URL, {
            'ids': [plain_field.id], 'groupId': group_id,
        }, format='json', HTTP_HOST='localhost')
        assert resp.status_code == 400, resp.content


# --- 组合属性与参数校验 -------------------------------------------------------


@pytest.mark.django_db
class TestBatchCombinedAndValidation:
    def test_both_attrs_together(self, client, plain_field, group_b):
        """fieldType + groupId 同时传 → 两项都生效。"""
        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id], 'fieldType': 'NUMBER', 'groupId': group_b.id,
        }, format='json', HTTP_HOST='localhost'))

        assert data['updatedCount'] == 1
        plain_field.refresh_from_db()
        assert plain_field.field_type == 'NUMBER'
        assert plain_field.group_id == group_b.id
        assert plain_field.module_id == group_b.module_id

    def test_unknown_id_skipped(self, client, plain_field):
        """未知 id → skipped(字段不存在或已删除), 不影响其余条目。"""
        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id, 'no_such_field_id'], 'fieldType': 'NUMBER',
        }, format='json', HTTP_HOST='localhost'))

        assert data['updated'] == [plain_field.id]
        assert len(data['skipped']) == 1
        assert data['skipped'][0]['id'] == 'no_such_field_id'
        assert '不存在' in data['skipped'][0]['reason']

    def test_ids_deduped(self, client, plain_field):
        """重复 id 去重后计入。"""
        data = _data(client.post(BATCH_URL, {
            'ids': [plain_field.id, plain_field.id], 'fieldType': 'NUMBER',
        }, format='json', HTTP_HOST='localhost'))
        assert data['requested'] == 1
        assert data['updatedCount'] == 1

    def test_empty_ids_returns_400(self, client):
        resp = client.post(BATCH_URL, {'ids': [], 'fieldType': 'NUMBER'}, format='json', HTTP_HOST='localhost')
        assert resp.status_code == 400, resp.content

    def test_missing_ids_returns_400(self, client):
        resp = client.post(BATCH_URL, {'fieldType': 'NUMBER'}, format='json', HTTP_HOST='localhost')
        assert resp.status_code == 400, resp.content

    def test_no_attrs_returns_400(self, client, plain_field):
        """只传 ids 不传属性 → 400。"""
        resp = client.post(BATCH_URL, {'ids': [plain_field.id]}, format='json', HTTP_HOST='localhost')
        assert resp.status_code == 400, resp.content
        assert '至少指定一项' in resp.json()['message']

    def test_invalid_field_type_returns_400(self, client, plain_field):
        resp = client.post(BATCH_URL, {
            'ids': [plain_field.id], 'fieldType': 'NOT_A_TYPE',
        }, format='json', HTTP_HOST='localhost')
        assert resp.status_code == 400, resp.content
        assert '不支持的字段类型' in resp.json()['message']

    def test_over_max_ids_returns_400(self, client):
        resp = client.post(BATCH_URL, {
            'ids': [f'f_{i}' for i in range(201)], 'fieldType': 'NUMBER',
        }, format='json', HTTP_HOST='localhost')
        assert resp.status_code == 400, resp.content
        assert '最多批量修改' in resp.json()['message']
