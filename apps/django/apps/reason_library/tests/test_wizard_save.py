"""Wizard 单测 (T12 part 2) — 事务回滚 + level>4 → 422 + 并发 OPTIMISTIC_LOCK_FAILED。

至少 4 条 pytest case.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from rest_framework.test import APIClient

from apps.reason_library.models import (
    CategoryAssignment,
    ReasonTag,
    RuleCategory,
    RuleSceneAssignment,
    SceneRule,
    TagType,
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


# 可选乐观锁: If-Match 不匹配 → 412, 整事务回滚
# ---------------------------------------------------------------------------

def test_wizard_save_optimistic_lock_failed(admin_api_client, custom_rule):
    client, _ = admin_api_client
    payload = _build_payload(name='lock-fail', categories=[], scenes=[])
    stale = (custom_rule.updated_at - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    resp = client.post(
        _wizard_url(custom_rule.id), payload, format='json',
        HTTP_IF_MATCH=stale,
    )
    assert resp.status_code == 412
    assert resp.json()['code'] == 41200
    # 事务回滚: 名字未变
    custom_rule.refresh_from_db()
    assert custom_rule.name != 'lock-fail'


# ---------------------------------------------------------------------------
# 乐观锁: If-Match 匹配 → 200
# ---------------------------------------------------------------------------

def test_wizard_save_optimistic_lock_match(admin_api_client, custom_rule):
    client, _ = admin_api_client
    payload = _build_payload(name='lock-ok', categories=[], scenes=[])
    if_match = custom_rule.updated_at.strftime('%Y-%m-%dT%H:%M:%S')
    resp = client.post(
        _wizard_url(custom_rule.id), payload, format='json',
        HTTP_IF_MATCH=if_match,
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Scene 冲突 → 409 + 事务回滚
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Item4 修订 (2026-09-21): 标签唯一性收窄为【规则内】
# 跨规则共享标签池合法; 同一规则内跨分类重复 → 40902
# ---------------------------------------------------------------------------

def test_same_tag_across_rules_ok(admin_api_client, custom_rule, reason_tag):
    """不同规则可共享同一标签 (跨规则复用标签池) → 200。"""
    client, admin = admin_api_client
    other_rule = SceneRule.objects.create(name='other-rule', is_system=False)
    cat_other = RuleCategory.objects.create(rule=other_rule, name='other-cat', level=1)
    CategoryAssignment.objects.create(category=cat_other, tag=reason_tag)

    # custom_rule 里也用同一标签 → 合法
    payload = _build_payload(
        name='cross-rule-share',
        categories=[
            {
                'clientId': 'cat-x',
                'parentClientId': None,
                'name': '分类 X',
                'order': 1,
                'allowCustom': True,
                'tagIds': [reason_tag.id],
            },
        ],
        scenes=[],
    )
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 200
    assert CategoryAssignment.objects.filter(tag=reason_tag).count() == 2


def test_same_tag_within_rule_conflict(admin_api_client, custom_rule, reason_tag):
    """同一规则内标签出现在两个分类 → 40902 TAG_ALREADY_ASSIGNED。"""
    client, _ = admin_api_client
    payload = _build_payload(
        name='dup-in-rule',
        categories=[
            {
                'clientId': 'cat-1',
                'parentClientId': None,
                'name': '分类 1',
                'order': 1,
                'allowCustom': True,
                'tagIds': [reason_tag.id],
            },
            {
                'clientId': 'cat-2',
                'parentClientId': None,
                'name': '分类 2',
                'order': 2,
                'allowCustom': True,
                'tagIds': [reason_tag.id],
            },
        ],
        scenes=[],
    )
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 409
    assert resp.json()['code'] == 40902  # TAG_ALREADY_ASSIGNED
    # 事务回滚: 无 assignments 残留
    assert CategoryAssignment.objects.filter(tag=reason_tag).count() == 0


# ---------------------------------------------------------------------------
# 显式 scene_assignments (2026-09-22 重构): 支持「场景A仅社招、场景B仅校招」子集,
# 而非 scenes×recruit_types 笛卡尔积; 空列表 → 清空全部绑定。
# ---------------------------------------------------------------------------

def test_wizard_save_explicit_scene_assignments_subset(admin_api_client, custom_rule):
    """显式 pairs 支持子集: 场景A仅社招, 场景B仅校招 → 只建 2 条, 而非笛卡尔积 4 条。"""
    client, _ = admin_api_client
    RuleSceneAssignment.objects.filter(rule=custom_rule).delete()  # 清空 fixture 预置, 保证状态干净
    payload = {
        'name': 'explicit-pairs',
        'description': 'subset',
        'enabled': True,
        'categories': [],
        'scene_assignments': [
            {'scene': '筛选不通过', 'recruit_type': 'social'},
            {'scene': '取消面试', 'recruit_type': 'campus'},
        ],
    }
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 200
    assigns = RuleSceneAssignment.objects.filter(rule=custom_rule)
    assert assigns.count() == 2
    got = {(a.scene, a.recruit_type) for a in assigns}
    assert got == {('筛选不通过', 'social'), ('取消面试', 'campus')}


def test_wizard_save_explicit_pairs_conflict(admin_api_client, custom_rule):
    """显式 pairs 中某组合被其他规则占用 → 409 RULE_SCENE_CONFLICT (40920)。"""
    other = SceneRule.objects.create(name='Other-Conflict', is_system=False)
    RuleSceneAssignment.objects.create(rule=other, scene='筛选不通过', recruit_type='social')
    client, _ = admin_api_client
    payload = {
        'name': 'explicit-conflict',
        'categories': [],
        'scene_assignments': [
            {'scene': '筛选不通过', 'recruit_type': 'social'},  # 已被 other 占用
        ],
    }
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 409
    assert resp.json()['code'] == 40920


def test_wizard_save_explicit_pairs_clears_when_empty(admin_api_client, custom_rule):
    """显式传空 scene_assignments → 清空该规则全部场景绑定 (回退笛卡尔积亦为空)。"""
    RuleSceneAssignment.objects.create(rule=custom_rule, scene='淘汰', recruit_type='social')
    client, _ = admin_api_client
    payload = {
        'name': 'explicit-clear',
        'categories': [],
        'scene_assignments': [],
    }
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 200
    assert RuleSceneAssignment.objects.filter(rule=custom_rule).count() == 0


# ---------------------------------------------------------------------------
# 区块颜色 (2026-09-23): color 落库 + 回显 + 空串=未自定义
# ---------------------------------------------------------------------------

def test_wizard_save_persists_category_color(admin_api_client, custom_rule):
    """一级分类存专属色; 非一级未设色落库空串; 非一级自定义色落库覆盖值。"""
    client, _ = admin_api_client
    payload = _build_payload(
        name='color-roundtrip',
        categories=[
            {
                'clientId': 'lv1',
                'parentClientId': None,
                'name': '一级分类',
                'order': 1,
                'allowCustom': False,
                'color': '#FF8800',
                'tagIds': [],
            },
            {
                'clientId': 'lv2-inherit',
                'parentClientId': 'lv1',
                'name': '二级-继承',
                'order': 1,
                'allowCustom': False,
                'color': '',  # 未自定义 → 落库空串
                'tagIds': [],
            },
            {
                'clientId': 'lv2-override',
                'parentClientId': 'lv1',
                'name': '二级-覆盖',
                'order': 2,
                'allowCustom': False,
                'color': '#0088FF',  # 自定义覆盖
                'tagIds': [],
            },
        ],
        scenes=[],
    )
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 200
    data = resp.json()['data']
    cats = {c['name']: c for c in data['categories']}
    # 一级存专属色
    assert cats['一级分类']['color'] == '#FF8800'
    # 二级-继承: 落库空串 (前端读时再推导继承)
    assert cats['二级-继承']['color'] == ''
    # 二级-覆盖: 落库自定义色
    assert cats['二级-覆盖']['color'] == '#0088FF'

    # DB 校验: 空串落库为 '' 而非 NULL
    db_lv1 = RuleCategory.objects.get(rule=custom_rule, name='一级分类')
    db_inherit = RuleCategory.objects.get(rule=custom_rule, name='二级-继承')
    db_override = RuleCategory.objects.get(rule=custom_rule, name='二级-覆盖')
    assert db_lv1.color == '#FF8800'
    assert db_inherit.color == ''
    assert db_override.color == '#0088FF'
    assert db_inherit.level == 2 and db_override.level == 2 and db_lv1.level == 1
    assert db_inherit.parent_id == db_lv1.id  # 拓扑父子关系正确落库


def test_flat_serializer_exposes_color(admin_api_client, custom_rule):
    """RuleCategoryFlatSerializer 在规则详情里回显 color 字段。"""
    client, _ = admin_api_client
    RuleCategory.objects.create(rule=custom_rule, name='flat-c', level=1, color='#123456')
    resp = client.get(f'/api/v1/reason-library/rules/{custom_rule.id}/')
    assert resp.status_code == 200
    cats = {c['name']: c for c in resp.json()['data']['categories']}
    assert cats['flat-c']['color'] == '#123456'
