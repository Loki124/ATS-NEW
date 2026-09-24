"""预置默认规则 (系统兜底) 行为测试 (2026-09-24).

核心契约 (用户原话):
- 「预置默认规则」是系统默认兜底: 覆盖全部场景×类型, 且不可调整 覆盖/名称/状态;
  除以上及规则名/状态外, 其他内容可调整。
- 其它规则在检查场景及入口覆盖时, 预置默认规则**不参与校验**。
- 业务应用时优先使用自定义规则; 未覆盖时使用默认规则。

覆盖:
1. get_active_rule 兜底: 无自定义规则覆盖 → 回退预置默认。
2. 自定义规则优先: 覆盖某 (场景,类型) → 该组合取自定义, 其余仍兜底。
3. 向导保存: 自定义规则可覆盖全部 (场景,类型) 而不 409 (预置默认被排除出冲突校验)。
4. SceneView GET 不把预置默认当成「场景占用」展示。
5. 预置默认规则名称锁定: PATCH 改名无效, isPresetDefault 标记正确返回。
"""
from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.reason_library.models import (
    PRESET_DEFAULT_RULE_NAME, RECRUIT_TYPES, SCENE_OPTIONS,
    RuleSceneAssignment, SceneRule,
)
from apps.reason_library.services.active_query_service import (
    get_active_rule, invalidate_active_cache,
)

pytestmark = pytest.mark.django_db

RULES = '/api/v1/reason-library/rules/'
SCENES = '/api/v1/reason-library/scenes/'


def _make_preset_default():
    return SceneRule.objects.create(
        name=PRESET_DEFAULT_RULE_NAME, is_system=True, enabled=True,
    )


def test_preset_default_fallback_when_no_custom_covers(admin_api_client):
    """无自定义规则覆盖任何 (场景,类型) → get_active_rule 兜底返回预置默认。"""
    preset = _make_preset_default()
    invalidate_active_cache()
    for scene in SCENE_OPTIONS:
        for rt in RECRUIT_TYPES:
            rule = get_active_rule(scene, rt)
            assert rule is not None, f'未兜底: {scene}/{rt}'
            assert rule.id == preset.id


def test_custom_rule_overrides_preset_default(admin_api_client):
    """自定义规则覆盖 (筛选不通过, social) → 该组合取自定义; 其余仍兜底。"""
    preset = _make_preset_default()
    custom = SceneRule.objects.create(name='Custom A', is_system=False, enabled=True)
    RuleSceneAssignment.objects.create(rule=custom, scene='筛选不通过', recruit_type='social')
    invalidate_active_cache()

    assert get_active_rule('筛选不通过', 'social').id == custom.id
    # 同一场景其它类型仍兜底
    assert get_active_rule('筛选不通过', 'campus').id == preset.id
    # 其它场景任意类型仍兜底
    assert get_active_rule('淘汰', 'social').id == preset.id
    assert get_active_rule('淘汰', 'campus').id == preset.id


def test_wizard_save_custom_can_cover_all_preset_excluded(admin_api_client):
    """自定义规则向导保存覆盖全部 6×2 → 200 (预置默认不参与冲突校验, 不 409)。"""
    _make_preset_default()
    custom = SceneRule.objects.create(name='Custom All', is_system=False, enabled=True)
    client, _ = admin_api_client

    assignments = [
        {'scene': s, 'recruit_type': rt} for s in SCENE_OPTIONS for rt in RECRUIT_TYPES
    ]
    payload = {
        'name': 'Custom All',
        'description': 'cover everything',
        'enabled': True,
        'categories': [],
        'scene_assignments': assignments,
    }
    resp = client.post(
        f'{RULES}{custom.id}/wizard/save/', payload, format='json',
    )
    assert resp.status_code == 200, resp.content.decode()
    # 确认确实写进了全部 12 个组合
    assert RuleSceneAssignment.objects.filter(rule=custom).count() == 12


def test_scene_view_excludes_preset_default(admin_api_client):
    """预置默认即使有 assignment, SceneView 也不把它当成『占用』展示。"""
    preset = _make_preset_default()
    # 绕过 UNIQUE 直接给预置默认挂一条 assignment (模拟遗留/migration 态)
    RuleSceneAssignment.objects.create(rule=preset, scene='筛选不通过', recruit_type='social')
    client, _ = admin_api_client
    resp = client.get(SCENES)
    assert resp.status_code == 200
    items = resp.json()['data']['items']
    occ = {(it['scene'], it['recruitType']): it.get('ruleId') for it in items}
    # 该组合不应回填预置默认规则的 id
    assert occ[('筛选不通过', 'social')] is None


def test_preset_default_name_locked_on_patch(admin_api_client):
    """PATCH 改名无效 + partial_update 返回 isPresetDefault 标记。"""
    preset = _make_preset_default()
    client, _ = admin_api_client
    resp = client.patch(
        f'{RULES}{preset.id}/',
        {'name': 'hacked-name', 'description': 'changed'},
        format='json',
    )
    assert resp.status_code == 200, resp.content.decode()
    body = resp.json()['data']
    assert body['name'] == PRESET_DEFAULT_RULE_NAME  # 名称锁定, 未被改
    assert body['isPresetDefault'] is True
    # 描述可改
    assert body['description'] == 'changed'
    preset.refresh_from_db()
    assert preset.name == PRESET_DEFAULT_RULE_NAME


def test_save_guard_blocks_second_preset_default(admin_api_client):
    """模型 save() 守卫: 第二条 is_system+预置默认名必 IntegrityError (全局仅一条硬约束)。"""
    _make_preset_default()
    with pytest.raises(IntegrityError):
        SceneRule.objects.create(
            name=PRESET_DEFAULT_RULE_NAME, is_system=True, enabled=True,
        )
    # 仍只有一条
    assert SceneRule.objects.filter(
        is_system=True, name=PRESET_DEFAULT_RULE_NAME,
    ).count() == 1


def test_api_rejects_second_preset_default_with_400(admin_api_client):
    """API 再创建预置默认规则 → 400 (validate_name 拦截同名), 且全局仍仅一条。"""
    _make_preset_default()
    client, _ = admin_api_client
    resp = client.post(
        RULES,
        {
            'name': PRESET_DEFAULT_RULE_NAME, 'is_system': True, 'enabled': True,
            'description': '', 'max_selectable_tags': 5,
        },
        format='json',
    )
    assert resp.status_code == 400, resp.content.decode()
    # 第二条被拒, 全局仍仅一条 (满足「只能有一条」)
    assert SceneRule.objects.filter(
        is_system=True, name=PRESET_DEFAULT_RULE_NAME,
    ).count() == 1
