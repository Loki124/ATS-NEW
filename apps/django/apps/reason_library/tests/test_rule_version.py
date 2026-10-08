"""规则版本历史 (Task C) — 端点 + 回滚穿透测试 (真实链路)。

覆盖:
- POST /rules/ 创建即落一条 changeKind='create' 的 v1 快照, 且自动分配 S+4 编号
- POST /rules/{id}/wizard/save/ 触发 version+1 并落 'update' 快照
- GET /rules/{id}/versions/ 倒序返回, 数量与 changeKind 正确
- POST /rules/{id}/versions/rollback/ 回滚到 v1 → 名称还原、version 再 +1、新增 'rollback' 快照
- 回滚不存在版本 → 404
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _wizard_payload(name: str, categories: list, scenes: list) -> dict:
    return {
        'name': name,
        'description': 'ver test',
        'enabled': True,
        'categories': categories,
        'scenes': scenes,
    }


def _create_rule(client: APIClient, name: str) -> str:
    resp = client.post(
        '/api/v1/reason-library/rules/',
        {'name': name, 'description': 'x'},
        format='json',
    )
    assert resp.status_code in (200, 201), resp.json()
    data = resp.json()['data']
    assert data['code'] and data['code'].startswith('S'), data
    assert data['version'] == 1, data
    return data['id']


def test_rule_version_create_and_rollback(admin_api_client, reason_tag):
    client, _ = admin_api_client
    rule_id = _create_rule(client, 'Ver Rule')

    # 2) 三步向导保存 → version 2 + update 快照
    payload = _wizard_payload(
        name='Ver Rule v2',
        categories=[{
            'clientId': 'cat-a',
            'parentClientId': None,
            'name': 'Cat A',
            'order': 1,
            'allowCustom': True,
            'tagIds': [reason_tag.id],
        }],
        scenes=['取消面试'],
    )
    resp = client.post(
        f'/api/v1/reason-library/rules/{rule_id}/wizard/save/',
        payload,
        format='json',
    )
    assert resp.status_code == 200, resp.json()
    data = resp.json()['data']
    assert data['version'] == 2, data
    assert '取消面试' in data['scenes'], data

    # 3) 版本列表: 2 条, 倒序, v2=update v1=create
    resp = client.get(f'/api/v1/reason-library/rules/{rule_id}/versions/')
    assert resp.status_code == 200, resp.json()
    versions = resp.json()['data']
    assert len(versions) == 2, versions
    assert versions[0]['version'] == 2 and versions[0]['changeKind'] == 'update', versions
    assert versions[1]['version'] == 1 and versions[1]['changeKind'] == 'create', versions

    # 4) 回滚到 v1 → 名称还原为 'Ver Rule', version 3
    resp = client.post(
        f'/api/v1/reason-library/rules/{rule_id}/versions/rollback/',
        {'version_no': 1},
        format='json',
    )
    assert resp.status_code == 200, resp.json()
    rolled = resp.json()['data']
    assert rolled['name'] == 'Ver Rule', rolled
    assert rolled['version'] == 3, rolled
    assert rolled['scenes'] == [], rolled  # v1 快照无场景绑定

    # 5) 回滚后版本列表 3 条, 首条为 rollback
    resp = client.get(f'/api/v1/reason-library/rules/{rule_id}/versions/')
    assert resp.status_code == 200, resp.json()
    versions = resp.json()['data']
    assert len(versions) == 3, versions
    assert versions[0]['version'] == 3 and versions[0]['changeKind'] == 'rollback', versions


def test_rule_version_rollback_missing_returns_404(admin_api_client):
    client, _ = admin_api_client
    rule_id = _create_rule(client, 'Ver Rule 404')

    resp = client.post(
        f'/api/v1/reason-library/rules/{rule_id}/versions/rollback/',
        {'version_no': 999},
        format='json',
    )
    assert resp.status_code == 404, resp.json()
    assert resp.json()['code'] == 40410, resp.json()
