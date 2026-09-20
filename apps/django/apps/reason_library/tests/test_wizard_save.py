"""Wizard 单测 (T12 part 2) — 事务回滚 + level>4 → 422 + 事务回滚。

至少 4 条 pytest case.
"""
from __future__ import annotations


import pytest
from rest_framework.test import APIClient

from apps.reason_library.models import (
    CategoryAssignment, ReasonTag, RuleCategory,
    RuleSceneAssignment, SceneRule, TagType,
)

pytestmark = pytest.mark.django_db


def _wizard_url(rule_id: str) -> str:
    return f'/api/v1/reason-library/rules/{rule_id}/wizard/save/'


def _build_payload(name: str, categories: list, scenes: list):
    return {
        'name': name,
        'description': 'wiz test',
        'enabled': True,
        'categories': categories,
        'scenes': scenes,
    }


# ---------------------------------------------------------------------------
# Happy path: 基础三步保存
# ---------------------------------------------------------------------------

def test_wizard_save_happy_path(admin_api_client, custom_rule, reason_tag):
    client, _ = admin_api_client
    payload = _build_payload(
        name='wiz-updated',
        categories=[
            {
                'clientId': 'cat-a',
                'parentClientId': None,
                'name': '新分类 A',
                'order': 1,
                'allowCustom': True,
                'tagIds': [reason_tag.id],
            },
        ],
        scenes=['取消面试'],
    )
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 200
    data = resp.json()['data']
    assert data['name'] == 'wiz-updated'
    assert len(data['categories']) == 1
    assert '取消面试' in data['scenes']


# ---------------------------------------------------------------------------
# 事务回滚: 校验失败时所有改动回滚
# ---------------------------------------------------------------------------

def test_wizard_save_rollback_on_level_exceed(admin_api_client, custom_rule, reason_tag):
    """5 层嵌套 → CATEGORY_LEVEL_EXCEED → 整事务回滚。"""
    client, _ = admin_api_client
    # 构造 5 层链: cat-1 → cat-2 → cat-3 → cat-4 → cat-5 (level=5 > MAX=4)
    cats = []
    for i in range(1, 6):
        cats.append({
            'clientId': f'cat-{i}',
            'parentClientId': f'cat-{i-1}' if i > 1 else None,
            'name': f'Level {i}',
            'order': i,
            'allowCustom': True,
            'tagIds': [],
        })
    # 先让 cat-1 存在但不带 tag, 确保回滚不残留
    RuleCategory.objects.create(rule=custom_rule, name='pre-existing', level=1)

    payload = _build_payload(
        name='wiz-rollback',
        categories=cats,
        scenes=[],
    )
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 400
    assert resp.json()['code'] == 40030  # CATEGORY_LEVEL_EXCEED
    # 校验事务回滚: pre-existing 仍在, 没有新增
    assert RuleCategory.objects.filter(rule=custom_rule, name='pre-existing').exists()
    new_cats = RuleCategory.objects.filter(rule=custom_rule).exclude(name='pre-existing')
    assert new_cats.count() == 0


def test_wizard_save_scene_conflict_rollback(admin_api_client, custom_rule):
    other = SceneRule.objects.create(name='Other', is_system=False)
    RuleSceneAssignment.objects.create(rule=other, scene='淘汰')

    client, _ = admin_api_client
    # 先让 custom_rule.name 改成 something, 验证冲突回滚后名字不变
    original_name = custom_rule.name
    payload = _build_payload(
        name='new-name-attempt',
        categories=[],
        scenes=['淘汰'],  # 已被 other 占用
    )
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 409
    assert resp.json()['code'] == 40920
    custom_rule.refresh_from_db()
    assert custom_rule.name == original_name


# ---------------------------------------------------------------------------
# 删除分类: wizard diff 删除 db 中存在但 payload 中未出现的分类
# ---------------------------------------------------------------------------

def test_wizard_save_deletes_missing_categories(admin_api_client, custom_rule):
    client, _ = admin_api_client
    # 先建一个旧分类
    old_cat = RuleCategory.objects.create(rule=custom_rule, name='to-delete', level=1)
    payload = _build_payload(
        name='wiz-del',
        categories=[],  # 空的 → old_cat 应被删
        scenes=[],
    )
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 200
    assert not RuleCategory.objects.filter(pk=old_cat.pk).exists()


# ---------------------------------------------------------------------------
# import JSON 入口 (T09)
# ---------------------------------------------------------------------------

def test_wizard_import_json_creates_rule(admin_api_client, reason_tag):
    """POST /rules/import/ 创建 custom rule。"""
    client, _ = admin_api_client
    payload = {
        'name': 'JSON 导入测试',
        'description': 'imported',
        'enabled': True,
        'categories': [
            {
                'clientId': 'cat-j1',
                'parentClientId': None,
                'name': '分类1',
                'order': 1,
                'allowCustom': True,
                'tagIds': [reason_tag.id],
            },
        ],
        'scenes': ['邀约标注'],
    }
    resp = client.post('/api/v1/reason-library/rules/import/', payload, format='json')
    assert resp.status_code == 201
    data = resp.json()['data']
    assert '导入' in data['name'] or data['name'] == 'JSON 导入测试'
    assert data['isSystem'] is False or data['is_system'] is False
