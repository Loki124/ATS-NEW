"""Scene 冲突测试 (T12 part 1) — UNIQUE(scene) 兜底 + 应用层先查重。

至少 4 条 pytest case.
"""
from __future__ import annotations

import pytest
from django.db import IntegrityError
from rest_framework.test import APIClient

from apps.reason_library.models import (
    RuleSceneAssignment, SceneRule,
)

pytestmark = pytest.mark.django_db

SCENES = '/api/v1/reason-library/scenes/'


def test_get_scenes_returns_twelve(admin_api_client):
    """GET /scenes/ 返 6 场景 × 2 招聘类型(social/campus) = 12 项。"""
    client, _ = admin_api_client
    resp = client.get(SCENES)
    assert resp.status_code == 200
    items = resp.json()['data']['items']
    assert len(items) == 12
    scenes = [it['scene'] for it in items]
    assert '筛选不通过' in scenes
    assert '淘汰' in scenes
    recruit_types = {it['recruitType'] for it in items}
    assert recruit_types == {'social', 'campus'}


def test_db_unique_scene_constraint():
    """DB 层 UNIQUE(scene) 兜底 — 同 scene 二次绑定 → IntegrityError。"""
    rule_a = SceneRule.objects.create(name='A', is_system=False)
    rule_b = SceneRule.objects.create(name='B', is_system=False)
    RuleSceneAssignment.objects.create(rule=rule_a, scene='标记失败')
    with pytest.raises(IntegrityError):
        RuleSceneAssignment.objects.create(rule=rule_b, scene='标记失败')


def test_put_scenes_bulk_replace(admin_api_client, custom_rule):
    """PUT /scenes/ 整表替换绑定。"""
    client, _ = admin_api_client
    RuleSceneAssignment.objects.create(rule=custom_rule, scene='筛选不通过')
    payload = {
        'items': [
            {'scene': '筛选不通过', 'ruleId': None},
            {'scene': '取消面试', 'ruleId': custom_rule.id},
            {'scene': '淘汰', 'ruleId': custom_rule.id},
        ]
    }
    resp = client.put(SCENES, payload, format='json')
    assert resp.status_code == 200
    items = resp.json()['data']['items']
    # 按 (scene, recruitType) 双键索引, 避免 social/campus 同 scene 碰撞
    mapping = {(it['scene'], it['recruitType']): it.get('ruleId') for it in items}
    assert mapping[('筛选不通过', 'social')] is None
    assert mapping[('取消面试', 'social')] == custom_rule.id
    assert mapping[('淘汰', 'social')] == custom_rule.id


def test_wizard_save_scene_conflict_409(admin_api_client, custom_rule):
    """Wizard save 把已绑 scene 切到当前 rule → 409 RULE_SCENE_CONFLICT。"""
    other = SceneRule.objects.create(name='Other', is_system=False)
    RuleSceneAssignment.objects.create(rule=other, scene='筛选不通过')

    client, _ = admin_api_client
    payload = {
        'name': custom_rule.name,
        'description': '',
        'enabled': True,
        'categories': [],
        'scenes': ['筛选不通过'],  # 已被 other 占用
    }
    resp = client.post(
        f'/api/v1/reason-library/rules/{custom_rule.id}/wizard/save/',
        payload,
        format='json',
    )
    assert resp.status_code == 409
    assert resp.json()['code'] == 40920  # RULE_SCENE_CONFLICT
