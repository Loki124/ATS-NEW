"""职级管理 CRUD 测试 (ATS-NEW: 组织管理扩展 2026-10-14).

覆盖 4 个资源: job-levels / job-level-categories /
job-level-grade-settings(current) / job-level-sequences(current).
复用 dictionary 范本的 auth_client fixture 模式.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.job_level.models import JobLevelCategory
from tests.fixtures_common import attach_super_admin

JOB_LEVEL_LIST = '/api/v1/job-levels/'
JOB_LEVEL_CATEGORY_LIST = '/api/v1/job-level-categories/'
JOB_LEVEL_GRADE_CURRENT = '/api/v1/job-level-grade-settings/current/'
JOB_LEVEL_SEQUENCE_CURRENT = '/api/v1/job-level-sequences/current/'

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client(db):
    user = get_user_model().objects.create_user(
        username='job_level_crud_user', password='Test@1234', employee_id='EJL001'
    )
    client = APIClient()
    client.force_authenticate(attach_super_admin(user))
    return client


@pytest.fixture
def category(db):
    return JobLevelCategory.objects.create(name='技术族', sort_order=1, is_enabled=True)


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------

def test_unauthenticated_create_job_level_401():
    resp = APIClient().post(JOB_LEVEL_LIST, {'name': 'x', 'category': 'y'}, format='json')
    assert resp.status_code == 401


def test_unauthenticated_grade_current_401():
    resp = APIClient().get(JOB_LEVEL_GRADE_CURRENT)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 职级 CRUD
# ---------------------------------------------------------------------------

def test_create_job_level_201(auth_client, category):
    resp = auth_client.post(
        JOB_LEVEL_LIST,
        {'name': 'P5', 'category': category.id, 'grade': 5, 'sortOrder': 1, 'remark': 'xx'},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()['data']
    assert body['name'] == 'P5'
    assert body['category'] == category.id
    assert body['categoryName'] == '技术族'
    assert body['grade'] == 5
    assert body['status'] == 'ACTIVE'


def test_duplicate_job_level_name_400(auth_client, category):
    payload = {'name': '唯一职级', 'category': category.id, 'grade': 1}
    assert auth_client.post(JOB_LEVEL_LIST, payload, format='json').status_code == 201
    dup = auth_client.post(JOB_LEVEL_LIST, payload, format='json')
    assert dup.status_code == 400, dup.content
    assert 'name' in dup.json()['errors']


def test_create_job_level_missing_category_400(auth_client):
    resp = auth_client.post(JOB_LEVEL_LIST, {'name': '无类别职级', 'grade': 1}, format='json')
    assert resp.status_code == 400, resp.content
    assert 'category' in resp.json()['errors']


def test_update_job_level_200(auth_client, category):
    created = auth_client.post(
        JOB_LEVEL_LIST, {'name': '旧职级', 'category': category.id, 'grade': 1}, format='json'
    ).json()['data']
    jid = created['id']
    resp = auth_client.put(
        f'{JOB_LEVEL_LIST}{jid}/',
        {'name': '新职级', 'category': category.id, 'grade': 2, 'sortOrder': 3},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    body = resp.json()['data']
    assert body['name'] == '新职级'
    assert body['grade'] == 2


def test_delete_job_level_204_and_excluded(auth_client, category):
    created = auth_client.post(
        JOB_LEVEL_LIST, {'name': '待删职级', 'category': category.id, 'grade': 1}, format='json'
    ).json()['data']
    jid = created['id']
    del_resp = auth_client.delete(f'{JOB_LEVEL_LIST}{jid}/')
    assert del_resp.status_code == 204
    list_resp = auth_client.get(JOB_LEVEL_LIST, {'page_size': 200})
    ids = [t['id'] for t in list_resp.json()['data']]
    assert jid not in ids


def test_recreate_soft_deleted_job_level_name_400(auth_client, category):
    """软删某职级名后, 重建同名 → 必须 400 (DB unique 坑位 + 校验双重兜底)。"""
    created = auth_client.post(
        JOB_LEVEL_LIST, {'name': '软删职级', 'category': category.id, 'grade': 1}, format='json'
    ).json()['data']
    jid = created['id']
    assert auth_client.delete(f'{JOB_LEVEL_LIST}{jid}/').status_code == 204
    recreate = auth_client.post(
        JOB_LEVEL_LIST, {'name': '软删职级', 'category': category.id, 'grade': 1}, format='json'
    )
    assert recreate.status_code == 400, recreate.content
    assert 'name' in recreate.json()['errors']


# ---------------------------------------------------------------------------
# 职级类别 CRUD
# ---------------------------------------------------------------------------

def test_create_category_201(auth_client):
    resp = auth_client.post(
        JOB_LEVEL_CATEGORY_LIST, {'name': '产品族', 'sortOrder': 2}, format='json'
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()['data']
    assert body['name'] == '产品族'
    assert body['status'] == 'ACTIVE'


def test_duplicate_category_name_400(auth_client):
    payload = {'name': '唯一类别'}
    assert auth_client.post(JOB_LEVEL_CATEGORY_LIST, payload, format='json').status_code == 201
    dup = auth_client.post(JOB_LEVEL_CATEGORY_LIST, payload, format='json')
    assert dup.status_code == 400, dup.content
    assert 'name' in dup.json()['errors']


def test_delete_category_204(auth_client):
    created = auth_client.post(
        JOB_LEVEL_CATEGORY_LIST, {'name': '待删类别'}, format='json'
    ).json()['data']
    cid = created['id']
    assert auth_client.delete(f'{JOB_LEVEL_CATEGORY_LIST}{cid}/').status_code == 204


# ---------------------------------------------------------------------------
# 单例: 职等上限 / 职级序列
# ---------------------------------------------------------------------------

def test_grade_setting_current_get_default(auth_client):
    resp = auth_client.get(JOB_LEVEL_GRADE_CURRENT)
    assert resp.status_code == 200, resp.content
    assert 'maxGrade' in resp.json()['data']


def test_grade_setting_current_put(auth_client):
    resp = auth_client.put(JOB_LEVEL_GRADE_CURRENT, {'maxGrade': 50}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.json()['data']['maxGrade'] == 50


def test_grade_setting_current_put_out_of_range_400(auth_client):
    resp = auth_client.put(JOB_LEVEL_GRADE_CURRENT, {'maxGrade': 5000}, format='json')
    assert resp.status_code == 400, resp.content


def test_sequence_setting_current_put(auth_client):
    resp = auth_client.put(
        JOB_LEVEL_SEQUENCE_CURRENT, {'managementEnabled': True}, format='json'
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()['data']['managementEnabled'] is True
