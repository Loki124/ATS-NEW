"""数据字典 CRUD 测试 (ATS-NEW: 只读模块升级为完整增删改查).

复用 test_api.py 的 ``auth_client`` fixture 模式 (APIClient + force_authenticate),
响应信封取 ``resp.json()['data']`` (camelCase). 不改动 test_api.py 既有用例.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.dictionary.models import DictionaryItem, DictionaryType

TYPE_LIST = '/api/v1/dictionary-types/'
ITEM_LIST = '/api/v1/dictionary-items/'

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client(db):
    user = get_user_model().objects.create_user(
        username='dict_crud_user', password='Test@1234', employee_id='EDC001'
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def stage_type(db):
    """自建一个自定义字典类型 (含一个种子项), 供字典项 CRUD 测试复用。

    注: 阶段类型已改为系统内置枚举, 不再经数据字典 recruitment_stage_type,
    故此处用独立自定义类型, 不依赖系统预置。
    """
    dt, _ = DictionaryType.objects.get_or_create(
        code='test_crud_type',
        defaults={'name': 'CRUD测试类型', 'is_enabled': True},
    )
    DictionaryItem.objects.get_or_create(
        type=dt, key='SEED_ITEM',
        defaults={'value': '种子项', 'sort_order': 1, 'is_active': True},
    )
    return dt


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------

def test_unauthenticated_create_type_401():
    resp = APIClient().post(TYPE_LIST, {'code': 'x', 'name': 'x'}, format='json')
    assert resp.status_code == 401


def test_unauthenticated_update_type_401():
    resp = APIClient().put(f'{TYPE_LIST}recruitment_stage_type/', {'name': 'x'}, format='json')
    assert resp.status_code == 401


def test_unauthenticated_delete_type_401():
    resp = APIClient().delete(f'{TYPE_LIST}recruitment_stage_type/')
    assert resp.status_code == 401


def test_unauthenticated_create_item_401():
    resp = APIClient().post(ITEM_LIST, {'type': 'x', 'key': 'k', 'value': 'v'}, format='json')
    assert resp.status_code == 401


def test_unauthenticated_update_item_401():
    resp = APIClient().put(f'{ITEM_LIST}abc/', {'value': 'v'}, format='json')
    assert resp.status_code == 401


def test_unauthenticated_delete_item_401():
    resp = APIClient().delete(f'{ITEM_LIST}abc/')
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 字典类型 CRUD
# ---------------------------------------------------------------------------

def test_create_dictionary_type_201(auth_client):
    resp = auth_client.post(
        TYPE_LIST,
        {'code': 'test_color', 'name': '颜色', 'description': '颜色字典'},
        format='json',
    )
    assert resp.status_code == 201
    body = resp.json()['data']
    assert body['code'] == 'test_color'
    assert body['name'] == '颜色'
    # code 非法 (含空格等非法字符) → 400
    bad = auth_client.post(TYPE_LIST, {'code': 'bad code', 'name': 'x'}, format='json')
    assert bad.status_code == 400


def test_duplicate_dictionary_type_code_400(auth_client):
    payload = {'code': 'test_lang', 'name': '语言'}
    assert auth_client.post(TYPE_LIST, payload, format='json').status_code == 201
    dup = auth_client.post(TYPE_LIST, payload, format='json')
    assert dup.status_code == 400
    assert 'code' in dup.json()['errors']


def test_update_dictionary_type_200(auth_client):
    auth_client.post(TYPE_LIST, {'code': 'test_status', 'name': '状态'}, format='json')
    resp = auth_client.put(f'{TYPE_LIST}test_status/', {'name': '状态(新)'}, format='json')
    assert resp.status_code == 200
    body = resp.json()['data']
    assert body['name'] == '状态(新)'
    # code 不可在编辑时修改 (仍保持原值)
    assert body['code'] == 'test_status'


def test_delete_dictionary_type_204_and_excluded(auth_client):
    auth_client.post(TYPE_LIST, {'code': 'test_dept', 'name': '部门'}, format='json')
    del_resp = auth_client.delete(f'{TYPE_LIST}test_dept/')
    assert del_resp.status_code == 204

    list_resp = auth_client.get(TYPE_LIST, {'page_size': 200})
    codes = [t['code'] for t in list_resp.json()['data']]
    assert 'test_dept' not in codes


# ---------------------------------------------------------------------------
# 字典项 CRUD (复用自建自定义类型 stage_type)
# ---------------------------------------------------------------------------

def test_create_dictionary_item_201(auth_client, stage_type):
    resp = auth_client.post(
        ITEM_LIST,
        {
            'type': stage_type.id,
            'key': 'TEST_ITEM_A',
            'value': '测试项A',
            'sortOrder': 100,
            'isActive': True,
        },
        format='json',
    )
    assert resp.status_code == 201
    body = resp.json()['data']
    assert body['key'] == 'TEST_ITEM_A'
    assert body['type'] == stage_type.id
    assert body['typeCode'] == 'test_crud_type'
    assert body['sortOrder'] == 100


def test_duplicate_dictionary_item_key_400(auth_client, stage_type):
    payload = {'type': stage_type.id, 'key': 'TEST_ITEM_DUP', 'value': 'v'}
    assert auth_client.post(ITEM_LIST, payload, format='json').status_code == 201
    dup = auth_client.post(ITEM_LIST, payload, format='json')
    assert dup.status_code == 400
    assert 'key' in dup.json()['errors']


def test_update_dictionary_item_200(auth_client, stage_type):
    created = auth_client.post(
        ITEM_LIST,
        {'type': stage_type.id, 'key': 'TEST_ITEM_U', 'value': '旧值', 'isActive': True},
        format='json',
    ).json()['data']
    item_id = created['id']
    resp = auth_client.put(f'{ITEM_LIST}{item_id}/', {'value': '新值', 'isActive': True}, format='json')
    assert resp.status_code == 200
    body = resp.json()['data']
    assert body['value'] == '新值'
    assert body['isActive'] is True
    # key 保持原值
    assert body['key'] == 'TEST_ITEM_U'


def test_delete_history_item_rejected_400(auth_client, stage_type):
    """历史字典项不支持删除（PRD 5.2），API 必须 400 拦截。"""
    created = auth_client.post(
        ITEM_LIST, {'type': stage_type.id, 'key': 'TEST_ITEM_D', 'value': '待删'}, format='json'
    ).json()['data']
    item_id = created['id']
    del_resp = auth_client.delete(f'{ITEM_LIST}{item_id}/')
    assert del_resp.status_code == 400, del_resp.content
    assert '删除' in str(del_resp.json()['errors']['detail'])

    # 项仍存在于列表
    list_resp = auth_client.get(ITEM_LIST, {'type_code': 'test_crud_type', 'page_size': 200})
    ids = [it['id'] for it in list_resp.json()['data']]
    assert item_id in ids


# ---------------------------------------------------------------------------
# 关键风险: 软删行仍占唯一约束坑位, 重建同名应被拦截为 400 (而非 500 / 200)
# ---------------------------------------------------------------------------

def test_duplicate_item_key_400(auth_client, stage_type):
    """重建同 type+key → 必须 400 (不能 500, 也不能 200 重复写入)。"""
    created = auth_client.post(
        ITEM_LIST, {'type': stage_type.id, 'key': 'TEST_ITEM_SOFT', 'value': '已存在'}, format='json'
    ).json()['data']
    item_id = created['id']

    # 同名 key 重建应被校验阶段拦截 → 400
    recreate = auth_client.post(
        ITEM_LIST, {'type': stage_type.id, 'key': 'TEST_ITEM_SOFT', 'value': '重复'}, format='json'
    )
    assert recreate.status_code == 400, recreate.content
    assert 'key' in recreate.json()['errors']


def test_recreate_soft_deleted_type_code_400(auth_client):
    """软删某 type code 后, 重建同 code → 必须 400 (不能 500, 也不能 200 重复写入)。"""
    auth_client.post(TYPE_LIST, {'code': 'test_soft_code', 'name': '软删前'}, format='json')
    assert auth_client.delete(f'{TYPE_LIST}test_soft_code/').status_code == 204

    recreate = auth_client.post(TYPE_LIST, {'code': 'test_soft_code', 'name': '软删后重建'}, format='json')
    assert recreate.status_code == 400, recreate.content
    assert 'code' in recreate.json()['errors']


def test_create_type_missing_code_400(auth_client):
    """创建字典类型缺 code → 必须 400 (非空校验不能在 create 阶段被 required=False 跳过)。

    设计约定 DictionaryTypeSerializer.validate_code 应保证 code 非空;
    若 code 缺省则 validate_code 不被调用, 会落出 code='' 的无效行 —— 这是源码缺陷,
    期望后端在 create 时对缺失 code 返回 400。
    """
    resp = auth_client.post(TYPE_LIST, {'name': '缺少编码'}, format='json')
    assert resp.status_code == 400, resp.content
    assert 'code' in resp.json()['errors']
