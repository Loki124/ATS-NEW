"""数据字典进阶测试: 系统/自定义差异化、树形、批量提交校验、列表搜索。

覆盖 PRD 关键约束: 系统字典不可删/不可停用; 历史元素不可删只能停用;
元素树形(父级存在/循环依赖); 批量提交(唯一性/停用含子级拦截); 列表搜索与类型筛选。
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.dictionary.models import DictionaryItem, DictionaryType

TYPE_LIST = '/api/v1/dictionary-types/'
SUBMIT = '/api/v1/dictionary-types/{code}/submit/'

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client(db):
    user = get_user_model().objects.create_user(
        username='dict_adv_user', password='Test@1234', employee_id='EDA001'
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def stage_type(db):
    """自建一个系统预置字典类型, 供系统/自定义差异化测试复用。

    注: 阶段类型已改为系统内置枚举, 不再经数据字典 recruitment_stage_type,
    故此处用独立系统类型验证「系统字典不可删/不可停用」约束。
    """
    dt, _ = DictionaryType.objects.get_or_create(
        code='test_system_type',
        defaults={'name': '系统测试类型', 'is_system': True, 'is_enabled': True},
    )
    return dt


@pytest.fixture
def custom_type(auth_client):
    """创建一个自定义字典（is_system=False），返回其 code。"""
    resp = auth_client.post(
        TYPE_LIST, {'code': 'custom_dept', 'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'}, format='json'
    )
    assert resp.status_code == 201, resp.content
    return resp.json()['data']['code']


# ---------------------------------------------------------------------------
# 系统 / 自定义差异化
# ---------------------------------------------------------------------------

def test_system_dict_delete_rejected_400(auth_client, stage_type):
    resp = auth_client.delete(f'{TYPE_LIST}{stage_type.code}/')
    assert resp.status_code == 400, resp.content
    assert '系统预置' in str(resp.json()['errors']['detail'])


def test_system_dict_disable_via_submit_rejected_400(auth_client, stage_type):
    resp = auth_client.post(
        SUBMIT.format(code=stage_type.code),
        {'head': {'is_enabled': False, 'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'}, 'items': []},
        format='json',
    )
    assert resp.status_code == 400, resp.content
    assert 'isEnabled' in resp.json()['headErrors']


def test_custom_dict_disable_via_submit_200(auth_client, custom_type):
    resp = auth_client.post(
        SUBMIT.format(code=custom_type),
        {'head': {'is_enabled': False, 'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'}, 'items': []},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    t = DictionaryType.objects.get(code=custom_type)
    assert t.is_enabled is False


def test_dict_number_auto_on_create(auth_client):
    resp = auth_client.post(
        TYPE_LIST, {'code': 'auto_num', 'name': '自动编号', 'english_name': 'AUTO_NUM'}, format='json'
    )
    assert resp.status_code == 201
    assert resp.json()['data']['dictNumber'].startswith('D'), resp.json()


# ---------------------------------------------------------------------------
# 批量提交: 树形 + 校验
# ---------------------------------------------------------------------------

def test_submit_create_tree_200(auth_client, custom_type):
    payload = {
        'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'},
        'items': [
            {'client_id': 'c1', 'key': 'P', 'value': '父级', 'sort_order': 1, 'is_active': True},
            {'client_id': 'c2', 'parent_client_id': 'c1', 'key': 'C', 'value': '子级',
             'sort_order': 2, 'is_active': True},
        ],
    }
    resp = auth_client.post(SUBMIT.format(code=custom_type), payload, format='json')
    assert resp.status_code == 200, resp.content

    detail = auth_client.get(f'{TYPE_LIST}{custom_type}/').json()['data']
    items = {it['key']: it for it in detail['items']}
    assert items['C']['parentId'] == items['P']['id']


def test_submit_duplicate_key_in_draft_400(auth_client, custom_type):
    payload = {
        'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'},
        'items': [
            {'client_id': 'c1', 'key': 'DUP', 'value': '甲', 'sort_order': 1, 'is_active': True},
            {'client_id': 'c2', 'key': 'DUP', 'value': '乙', 'sort_order': 2, 'is_active': True},
        ],
    }
    resp = auth_client.post(SUBMIT.format(code=custom_type), payload, format='json')
    assert resp.status_code == 400, resp.content
    assert '0' in resp.json()['itemErrors']


def test_submit_key_conflict_with_db_400(auth_client, custom_type):
    # 先落库一个 key
    auth_client.post(
        SUBMIT.format(code=custom_type),
        {'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'}, 'items': [{'client_id': 'c1', 'key': 'EXIST', 'value': '已存在',
                                'sort_order': 1, 'is_active': True}]},
        format='json',
    )
    # 再提交相同 key
    resp = auth_client.post(
        SUBMIT.format(code=custom_type),
        {'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'}, 'items': [{'client_id': 'c2', 'key': 'EXIST', 'value': '冲突',
                                'sort_order': 2, 'is_active': True}]},
        format='json',
    )
    assert resp.status_code == 400, resp.content
    assert 'key' in resp.json()['itemErrors']['0']


def test_submit_parent_not_exist_400(auth_client, custom_type):
    payload = {
        'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'},
        'items': [
            {'client_id': 'c1', 'parent_id': 'nonexistent_id', 'key': 'X', 'value': 'x',
             'sort_order': 1, 'is_active': True},
        ],
    }
    resp = auth_client.post(SUBMIT.format(code=custom_type), payload, format='json')
    assert resp.status_code == 400, resp.content
    assert 'parentId' in resp.json()['itemErrors']['0']


def test_submit_cycle_detection_400(auth_client, custom_type):
    # c1 父 = c2, c2 父 = c1 → 循环
    payload = {
        'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'},
        'items': [
            {'client_id': 'c1', 'parent_client_id': 'c2', 'key': 'A', 'value': 'a',
             'sort_order': 1, 'is_active': True},
            {'client_id': 'c2', 'parent_client_id': 'c1', 'key': 'B', 'value': 'b',
             'sort_order': 2, 'is_active': True},
        ],
    }
    resp = auth_client.post(SUBMIT.format(code=custom_type), payload, format='json')
    assert resp.status_code == 400, resp.content
    assert 'parentId' in resp.json()['itemErrors']['0']


def test_submit_deactivate_with_children_400(auth_client, custom_type):
    # 先建父+子
    auth_client.post(
        SUBMIT.format(code=custom_type),
        {'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'}, 'items': [
            {'client_id': 'p', 'key': 'PA', 'value': '父', 'sort_order': 1, 'is_active': True},
            {'client_id': 'c', 'parent_client_id': 'p', 'key': 'CA', 'value': '子',
             'sort_order': 2, 'is_active': True},
        ]},
        format='json',
    )
    detail = auth_client.get(f'{TYPE_LIST}{custom_type}/').json()['data']
    parent = next(it for it in detail['items'] if it['key'] == 'PA')
    child = next(it for it in detail['items'] if it['key'] == 'CA')
    # 停用父（子仍启用）→ 拦截
    resp = auth_client.post(
        SUBMIT.format(code=custom_type),
        {'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'}, 'items': [
            {'id': parent['id'], 'key': 'PA', 'value': '父', 'sort_order': 1, 'is_active': False},
            {'id': child['id'], 'parent_id': parent['id'], 'key': 'CA', 'value': '子', 'sort_order': 2, 'is_active': True},
        ]},
        format='json',
    )
    assert resp.status_code == 400, resp.content


def test_submit_deactivate_leaf_200(auth_client, custom_type):
    auth_client.post(
        SUBMIT.format(code=custom_type),
        {'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'}, 'items': [{'client_id': 'c', 'key': 'LEAF', 'value': '叶',
                                'sort_order': 1, 'is_active': True}]},
        format='json',
    )
    detail = auth_client.get(f'{TYPE_LIST}{custom_type}/').json()['data']
    leaf = detail['items'][0]
    resp = auth_client.post(
        SUBMIT.format(code=custom_type),
        {'head': {'name': '自定义部门', 'english_name': 'CUSTOM_DEPT'}, 'items': [{'id': leaf['id'], 'key': 'LEAF', 'value': '叶',
                                'sort_order': 1, 'is_active': False}]},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    assert not DictionaryItem.objects.get(id=leaf['id']).is_active


def test_submit_head_name_empty_400(auth_client, custom_type):
    resp = auth_client.post(
        SUBMIT.format(code=custom_type),
        {'head': {'name': '', 'english_name': 'X'}, 'items': []},
        format='json',
    )
    assert resp.status_code == 400, resp.content
    assert 'name' in resp.json()['headErrors']


# ---------------------------------------------------------------------------
# 单独切换启用/停用 (PATCH 部分更新)
# ---------------------------------------------------------------------------

def test_type_toggle_disable_via_patch_200(auth_client, custom_type):
    """列表页"停用"按钮只传 is_enabled, 后端须用 PATCH 部分更新接受 (不要求 name)。"""
    resp = auth_client.patch(f'{TYPE_LIST}{custom_type}/', {'is_enabled': False}, format='json')
    assert resp.status_code == 200, resp.content
    assert DictionaryType.objects.get(code=custom_type).is_enabled is False


def test_type_toggle_enable_via_patch_200(auth_client, custom_type):
    DictionaryType.objects.filter(code=custom_type).update(is_enabled=False)
    resp = auth_client.patch(f'{TYPE_LIST}{custom_type}/', {'is_enabled': True}, format='json')
    assert resp.status_code == 200, resp.content
    assert DictionaryType.objects.get(code=custom_type).is_enabled is True


def test_type_update_full_put_requires_name_400(auth_client, custom_type):
    """PUT 全量更新缺 name 仍应 400 (契约不变, 前端须用 PATCH 而非 PUT 切换)。"""
    resp = auth_client.put(f'{TYPE_LIST}{custom_type}/', {'is_enabled': True}, format='json')
    assert resp.status_code == 400, resp.content


# ---------------------------------------------------------------------------
# 列表搜索 / 筛选
# ---------------------------------------------------------------------------

def test_list_search_by_element_name(auth_client, stage_type):
    # test_system_type 名称含 "系统测试"
    resp = auth_client.get(TYPE_LIST, {'q': '系统测试', 'page_size': 200})
    codes = [t['code'] for t in resp.json()['data']]
    assert 'test_system_type' in codes


def test_list_filter_system(auth_client, stage_type, custom_type):
    resp = auth_client.get(TYPE_LIST, {'type': 'system', 'page_size': 200})
    codes = [t['code'] for t in resp.json()['data']]
    assert 'test_system_type' in codes
    assert custom_type not in codes

    resp = auth_client.get(TYPE_LIST, {'type': 'custom', 'page_size': 200})
    codes = [t['code'] for t in resp.json()['data']]
    assert custom_type in codes
    assert 'test_system_type' not in codes


def test_list_filter_is_enabled(auth_client, stage_type, custom_type):
    """启用状态筛选: is_enabled=true 仅返回启用项; =false 仅返回停用项。"""
    # test_system_type 默认启用; custom_type 先停用
    auth_client.patch(f'{TYPE_LIST}{custom_type}/', {'is_enabled': False}, format='json')

    resp = auth_client.get(TYPE_LIST, {'is_enabled': 'true', 'page_size': 200})
    codes = [t['code'] for t in resp.json()['data']]
    assert 'test_system_type' in codes
    assert custom_type not in codes

    resp = auth_client.get(TYPE_LIST, {'is_enabled': 'false', 'page_size': 200})
    codes = [t['code'] for t in resp.json()['data']]
    assert custom_type in codes
    assert 'test_system_type' not in codes
