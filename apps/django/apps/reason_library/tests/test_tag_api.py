"""Tag API 单测 (T10) — 覆盖 E-01/07/08/09/11/12 + AC.

至少 12 条 pytest case.
"""
from __future__ import annotations

import io

import pytest
from rest_framework.test import APIClient

from apps.reason_library.models import (
    CategoryAssignment, ReasonTag, RuleCategory, RuleSceneAssignment,
    TagType,
)

pytestmark = pytest.mark.django_db

TAG_LIST = '/api/v1/reason-library/tags/'
TAG_IMPORT = '/api/v1/reason-library/tags/import/'


# ---------------------------------------------------------------------------
# 鉴权 (E-12)
# ---------------------------------------------------------------------------

def test_list_tags_unauthenticated_401():
    resp = APIClient().get(TAG_LIST)
    assert resp.status_code == 401


def test_list_tags_authenticated_200(auth_api_client):
    client, _ = auth_api_client
    resp = client.get(TAG_LIST)
    assert resp.status_code == 200
    assert resp.json()['code'] == 0


def test_create_tag_unauthenticated_401():
    resp = APIClient().post(TAG_LIST, {'name': 'whatever'}, format='json')
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# E-01: 系统标签不可改/不可删
# ---------------------------------------------------------------------------

def test_system_tag_patch_ok(admin_api_client, system_tag):
    """系统标签已放开编辑 (item1, 2026-09-21): 所有可访问用户均可改名。"""
    client, _ = admin_api_client
    resp = client.patch(f'{TAG_LIST}{system_tag.id}/', {'name': 'new-name'}, format='json')
    assert resp.status_code == 200
    system_tag.refresh_from_db()
    assert system_tag.name == 'new-name'


def test_system_tag_delete_403(admin_api_client, system_tag):
    client, _ = admin_api_client
    resp = client.delete(f'{TAG_LIST}{system_tag.id}/')
    assert resp.status_code == 403
    assert resp.json()['code'] == 40301


def test_system_tag_patch_enabled_403(admin_api_client, system_tag):
    """系统预置标签禁止调整状态 (2026-09-21): 改 enabled 应 403 SYSTEM_TAG_IMMUTABLE。"""
    client, _ = admin_api_client
    resp = client.patch(f'{TAG_LIST}{system_tag.id}/', {'enabled': False}, format='json')
    assert resp.status_code == 403
    assert resp.json()['code'] == 40301  # SYSTEM_TAG_IMMUTABLE
    # 状态未被改动
    system_tag.refresh_from_db()
    assert system_tag.enabled is True


# ---------------------------------------------------------------------------
# E-07: 自定义可启停 + 可删 (未被引用)
# ---------------------------------------------------------------------------

def test_custom_tag_patch_enabled_ok(admin_api_client, reason_tag):
    client, _ = admin_api_client
    resp = client.patch(f'{TAG_LIST}{reason_tag.id}/', {'enabled': False}, format='json')
    assert resp.status_code == 200
    reason_tag.refresh_from_db()
    assert reason_tag.enabled is False


def test_custom_tag_delete_ok(admin_api_client, reason_tag):
    client, _ = admin_api_client
    resp = client.delete(f'{TAG_LIST}{reason_tag.id}/')
    assert resp.status_code == 200
    reason_tag.refresh_from_db()
    assert reason_tag.deleted_at is not None


# ---------------------------------------------------------------------------
# E-09: 同名报错 (Q-A4 含软删)
# ---------------------------------------------------------------------------

def test_duplicate_name_returns_40001(admin_api_client, reason_tag):
    client, _ = admin_api_client
    resp = client.post(TAG_LIST, {'name': reason_tag.name}, format='json')
    assert resp.status_code == 400
    assert resp.json()['code'] == 40001  # TAG_NAME_DUPLICATED


def test_soft_deleted_name_cannot_reuse(admin_api_client, reason_tag):
    """Q-A4: 软删后的 name 不复用 → 400。"""
    client, _ = admin_api_client
    reason_tag.soft_delete()
    resp = client.post(TAG_LIST, {'name': reason_tag.name}, format='json')
    assert resp.status_code == 400
    assert resp.json()['code'] == 40001


# ---------------------------------------------------------------------------
# E-11: 被引用不可删
# ---------------------------------------------------------------------------

def test_tag_with_refs_cannot_delete(admin_api_client, reason_tag, custom_rule):
    client, _ = admin_api_client
    cat = RuleCategory.objects.create(rule=custom_rule, name='ref-cat')
    CategoryAssignment.objects.create(category=cat, tag=reason_tag)
    resp = client.delete(f'{TAG_LIST}{reason_tag.id}/')
    assert resp.status_code == 409
    assert resp.json()['code'] == 40901  # TAG_HAS_REFS
    extra = resp.json().get('extra') or {}
    assert (extra.get('refCount') or extra.get('ref_count')) == 1


# ---------------------------------------------------------------------------
# E-08: 停用过滤业务态 (active endpoint)
# ---------------------------------------------------------------------------

def test_disabled_tag_excluded_from_active(admin_api_client, reason_tag, custom_rule):
    """E-08: 停用标签不进 active 规则的 tag_ids 列表。"""
    client, _ = admin_api_client
    cat = RuleCategory.objects.create(rule=custom_rule, name='cat', allow_custom=True, level=1)
    CategoryAssignment.objects.create(category=cat, tag=reason_tag)
    # 用未被 seed 占用的 scene (seed 占了 4 个: 筛选不通过/淘汰/取消面试/放入人才库)
    RuleSceneAssignment.objects.create(rule=custom_rule, scene='标记失败')

    # 停用标签
    reason_tag.enabled = False
    reason_tag.save(update_fields=['enabled', 'updated_at'])

    resp = client.get('/api/v1/reason-library/active/?scene=标记失败')
    assert resp.status_code == 200
    data = resp.json()['data']
    # 规则应可见, 但其 categories 里应不包含已停用标签
    assert data is not None
    cats = data.get('categories', [])
    tag_ids_per_cat = []
    for c in cats:
        tag_ids_per_cat.append(c.get('tagIds') or c.get('tag_ids') or [])
    # reason_tag.id 不应出现在任何分类的 tag_ids 中
    flat = [tid for ids in tag_ids_per_cat for tid in ids]
    assert reason_tag.id not in flat


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------

def test_csv_import_creates_tags(admin_api_client):
    client, _ = admin_api_client
    csv_content = 'name,en_name,tip,type,enabled\ncsv-tag-1,CSV Tag 1,tip1,custom,true\ncsv-tag-2,CSV Tag 2,,custom,false\n'
    upload = io.BytesIO(csv_content.encode('utf-8'))
    upload.name = 'tags.csv'
    resp = client.post(TAG_IMPORT, {'file': upload}, format='multipart')
    assert resp.status_code == 200
    body = resp.json()
    assert body['code'] == 0
    assert body['data']['created'] == 2


def test_csv_import_duplicate_returns_40001(admin_api_client, reason_tag):
    client, _ = admin_api_client
    csv_content = f'name,en_name,tip,type,enabled\n{reason_tag.name},X,X,custom,true\n'
    upload = io.BytesIO(csv_content.encode('utf-8'))
    upload.name = 'dup.csv'
    resp = client.post(TAG_IMPORT, {'file': upload}, format='multipart')
    assert resp.status_code == 400
    assert resp.json()['code'] == 40001
