"""F4 —— 字典批量提交的 N+1 回归（2026-10-21）

**缺陷**：`DictionaryTypeViewSet.submit`（批量提交）处理「已存在项」时，每条都做 2 次查询：
① `DictionaryItem.objects.get(id=p['item_id'], ...)`；
② `_has_children_final()` 内的 `DictionaryItem.objects.filter(parent=item, ...)`
→ N 条 = **2N 次查询**（导入 500 条就是 1000 次往返）。

**修法**：批量预取 —— 一次取全部已存在项 + 一次取全部子级映射，循环内零查询。

**本文件锁死**：SELECT 次数**不随条目数增长**（用两条不同 N 的批量做对比，
而不是写死一个魔法数字 —— 数字会随无关改动漂移，对比法不会）。
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.dictionary.models import DictionaryItem, DictionaryType
from tests.fixtures_common import attach_super_admin

TYPE_LIST = '/api/v1/dictionary-types/'
SUBMIT = '/api/v1/dictionary-types/{code}/submit/'


@pytest.fixture
def auth_client(db):
    user = get_user_model().objects.create_user(
        username='dict_n1_user', password='Test@1234', employee_id='FN1001'
    )
    client = APIClient()
    client.force_authenticate(attach_super_admin(user))
    return client


@pytest.fixture
def custom_type(auth_client):
    resp = auth_client.post(
        TYPE_LIST,
        {'code': 'n1_dept', 'name': 'N+1 测试部门', 'english_name': 'N1_DEPT'},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    return resp.json()['data']['code']


def _seed_items(auth_client, code, n, prefix='K'):
    """先建 n 个字典项, 返回它们的 id 列表。"""
    payload = {
        'head': {'name': 'N+1 测试部门', 'english_name': 'N1_DEPT'},
        'items': [
            {'client_id': f'c{prefix}{i}', 'key': f'{prefix}{i}', 'value': f'值{i}',
             'sort_order': i, 'is_active': True}
            for i in range(n)
        ],
    }
    resp = auth_client.post(SUBMIT.format(code=code), payload, format='json')
    assert resp.status_code == 200, resp.content
    dtype = DictionaryType.objects.get(code=code)
    items = list(
        DictionaryItem.objects.filter(
            type=dtype, deleted_at__isnull=True, key__startswith=prefix,
        ).order_by('sort_order')
    )
    assert len(items) == n
    return [it.id for it in items]


def _submit_existing(auth_client, code, item_ids, prefix='K'):
    """把已存在的 n 项各更新一次 (全部命中「已存在项」分支)。

    prefix 必须与 seed 时的 key 前缀一致 —— key 在库内唯一, 改成别的会撞「已存在」校验。
    """
    payload = {
        'head': {'name': 'N+1 测试部门', 'english_name': 'N1_DEPT'},
        'items': [
            {'client_id': f'u{i}', 'id': item_id, 'key': f'{prefix}{i}', 'value': f'改值{i}',
             'sort_order': i, 'is_active': True}
            for i, item_id in enumerate(item_ids)
        ],
    }
    with CaptureQueriesContext(connection) as ctx:
        resp = auth_client.post(SUBMIT.format(code=code), payload, format='json')
    assert resp.status_code == 200, resp.content
    selects = [
        q['sql'] for q in ctx.captured_queries
        if q['sql'].lstrip().upper().startswith('SELECT')
    ]
    return len(selects)


@pytest.mark.django_db
def test_batch_update_select_count_not_growing_with_items(auth_client, custom_type):
    """3 条 vs 9 条的 SELECT 次数应基本一致 (原为 2N → 差 12 次)。"""
    ids_small = _seed_items(auth_client, custom_type, 3)
    small = _submit_existing(auth_client, custom_type, ids_small)

    ids_big = _seed_items(auth_client, custom_type, 9, prefix='M')
    big = _submit_existing(auth_client, custom_type, ids_big, prefix='M')

    # 允许少量固定差 (如按 id 集合大小变化的 IN 查询仍算 1 次, 但 9 条可能多几次校验查询)
    # 关键: 增长不能是线性的 (原 3 条=6 次, 9 条=18 次, 差 12)。
    assert big - small < 6, (
        f'SELECT 次数随条目数线性增长 (3 条={small}, 9 条={big}) → N+1 未消除'
    )
    assert small <= 12, f'3 条也要 {small} 次 SELECT, 预期 O(1) 预取'


@pytest.mark.django_db
def test_batch_update_still_applies_values(auth_client, custom_type):
    """N+1 改造不能丢业务语义: 值确实被更新了。"""
    ids = _seed_items(auth_client, custom_type, 3)
    _submit_existing(auth_client, custom_type, ids)

    dtype = DictionaryType.objects.get(code=custom_type)
    items = {
        it.key: it for it in
        DictionaryItem.objects.filter(type=dtype, deleted_at__isnull=True)
    }
    assert items['K0'].value == '改值0'
    assert items['K2'].value == '改值2'


@pytest.mark.django_db
def test_batch_update_missing_item_still_400(auth_client, custom_type):
    """不存在的 item_id → 仍是 400（不是 500），语义未变。"""
    _seed_items(auth_client, custom_type, 2)
    payload = {
        'head': {'name': 'N+1 测试部门', 'english_name': 'N1_DEPT'},
        'items': [
            {'client_id': 'u0', 'id': 'not-exist-id', 'key': 'X', 'value': 'x',
             'sort_order': 0, 'is_active': True},
        ],
    }
    resp = auth_client.post(SUBMIT.format(code=custom_type), payload, format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_has_children_final_keeps_same_semantics(auth_client, custom_type):
    """有 live 子级的父项不可停用 —— 预取路径与单查路径判定一致。"""
    payload = {
        'head': {'name': 'N+1 测试部门', 'english_name': 'N1_DEPT'},
        'items': [
            {'client_id': 'p1', 'key': 'P', 'value': '父级', 'sort_order': 1, 'is_active': True},
            {'client_id': 'c1', 'parent_client_id': 'p1', 'key': 'C', 'value': '子级',
             'sort_order': 2, 'is_active': True},
        ],
    }
    resp = auth_client.post(SUBMIT.format(code=custom_type), payload, format='json')
    assert resp.status_code == 200, resp.content

    detail = auth_client.get(f'{TYPE_LIST}{custom_type}/').json()['data']
    items = {it['key']: it for it in detail['items']}
    parent_id = items['P']['id']

    # 停用父级 → 有子级 → 400
    payload2 = {
        'head': {'name': 'N+1 测试部门', 'english_name': 'N1_DEPT'},
        'items': [
            {'client_id': 'u1', 'id': parent_id, 'key': 'P', 'value': '父级',
             'sort_order': 1, 'is_active': False},
            {'client_id': 'u2', 'id': items['C']['id'], 'parent_id': parent_id,
             'key': 'C', 'value': '子级', 'sort_order': 2, 'is_active': True},
        ],
    }
    resp2 = auth_client.post(SUBMIT.format(code=custom_type), payload2, format='json')
    assert resp2.status_code == 400, resp2.content
    assert '子级' in resp2.json().get('detail', '')
