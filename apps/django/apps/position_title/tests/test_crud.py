"""职务管理 CRUD 测试 (ATS-NEW: 组织管理扩展 2026-10-14).

复用 dictionary 范本的 auth_client fixture 模式 (APIClient + force_authenticate),
响应信封取 resp.json()['data'] (camelCase). 不改动 test_api.py 既有用例.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from tests.fixtures_common import attach_super_admin
from rest_framework.test import APIClient

from apps.dictionary.models import DictionaryType, DictionaryItem

POSITION_TITLE_LIST = '/api/v1/position-titles/'

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client(db):
    user = get_user_model().objects.create_user(
        username='job_title_crud_user', password='Test@1234', employee_id='EJT001'
    )
    client = APIClient()
    client.force_authenticate(attach_super_admin(user))
    return client


@pytest.fixture
def family_item(db):
    """建一个未软删的职位族字典项, 供职务 FK 引用。"""
    dt, _ = DictionaryType.objects.get_or_create(
        code='test_position_family',
        defaults={'name': '测试职位族'},
    )
    item, _ = DictionaryItem.objects.get_or_create(
        type=dt, key='FAM_TEST',
        defaults={'value': '测试族', 'sort_order': 1, 'is_active': True},
    )
    return item


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------

def test_unauthenticated_create_401():
    resp = APIClient().post(POSITION_TITLE_LIST, {'name': 'x'}, format='json')
    assert resp.status_code == 401


def test_unauthenticated_delete_401():
    resp = APIClient().delete(f'{POSITION_TITLE_LIST}abc/')
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 职务 CRUD
# ---------------------------------------------------------------------------

def test_create_job_title_201(auth_client, family_item):
    resp = auth_client.post(
        POSITION_TITLE_LIST,
        {'name': '后端工程师', 'jobFamily': family_item.id},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()['data']
    assert body['name'] == '后端工程师'
    assert body['jobFamily'] == family_item.id
    assert body['jobFamilyName'] == '测试族'
    assert body['status'] == 'ACTIVE'


def test_duplicate_job_title_name_400(auth_client, family_item):
    payload = {'name': '唯一职务', 'jobFamily': family_item.id}
    assert auth_client.post(POSITION_TITLE_LIST, payload, format='json').status_code == 201
    dup = auth_client.post(POSITION_TITLE_LIST, payload, format='json')
    assert dup.status_code == 400, dup.content
    assert 'name' in dup.json()['errors']


def test_create_job_title_missing_name_400(auth_client, family_item):
    resp = auth_client.post(POSITION_TITLE_LIST, {'jobFamily': family_item.id}, format='json')
    assert resp.status_code == 400, resp.content
    assert 'name' in resp.json()['errors']


def test_create_job_title_missing_family_400(auth_client):
    resp = auth_client.post(POSITION_TITLE_LIST, {'name': '无族职务'}, format='json')
    assert resp.status_code == 400, resp.content
    assert 'jobFamily' in resp.json()['errors']


def test_update_job_title_200(auth_client, family_item):
    created = auth_client.post(
        POSITION_TITLE_LIST, {'name': '旧职务名', 'jobFamily': family_item.id}, format='json'
    ).json()['data']
    tid = created['id']
    resp = auth_client.put(
        f'{POSITION_TITLE_LIST}{tid}/',
        {'name': '新职务名', 'jobFamily': family_item.id, 'isKeyPosition': True},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    body = resp.json()['data']
    assert body['name'] == '新职务名'
    assert body['isKeyPosition'] is True


def test_delete_job_title_204_and_excluded(auth_client, family_item):
    created = auth_client.post(
        POSITION_TITLE_LIST, {'name': '待删职务', 'jobFamily': family_item.id}, format='json'
    ).json()['data']
    tid = created['id']
    del_resp = auth_client.delete(f'{POSITION_TITLE_LIST}{tid}/')
    assert del_resp.status_code == 204
    list_resp = auth_client.get(POSITION_TITLE_LIST, {'page_size': 200})
    ids = [t['id'] for t in list_resp.json()['data']]
    assert tid not in ids


def test_recreate_soft_deleted_name_400(auth_client, family_item):
    """软删某职务名后, 重建同名 → 必须 400 (DB unique 坑位 + 校验双重兜底)。"""
    created = auth_client.post(
        POSITION_TITLE_LIST, {'name': '软删职务', 'jobFamily': family_item.id}, format='json'
    ).json()['data']
    tid = created['id']
    assert auth_client.delete(f'{POSITION_TITLE_LIST}{tid}/').status_code == 204
    recreate = auth_client.post(
        POSITION_TITLE_LIST, {'name': '软删职务', 'jobFamily': family_item.id}, format='json'
    )
    assert recreate.status_code == 400, recreate.content
    assert 'name' in recreate.json()['errors']
