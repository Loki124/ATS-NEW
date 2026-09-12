"""重复候选人管理 API 测试

覆盖：
- catalog / config 读写 + 未知键拒绝
- rules 惰性种入系统规则、自定义规则 CRUD、约束校验、系统规则删除保护、toggle、reset
- camelCase 边界：项目全局启用 CamelCaseJSONParser/Renderer，
  前端发 camelCase、后端存 snake_case、响应回 camelCase —— 属硬契约，必须有用例守住

认证复用 tests/fixtures_common 的 auth_client（V2 super_user + JWT），
否则会被全局 IsAuthenticatedDenyByDefault 拦成 403。
"""
import json

import pytest

from apps.duplicate_rule.catalog import DEFAULT_RULES
from apps.duplicate_rule.models import DuplicateConfig, DuplicateRule

pytestmark = pytest.mark.django_db

RULES_URL = '/api/v1/duplicate-rules/rules/'


# ============================================================
# catalog
# ============================================================
def test_catalog_returns_three_strength_groups(auth_client):
    resp = auth_client.get('/api/v1/duplicate-rules/catalog/')
    assert resp.status_code == 200
    groups = resp.data['data']['groups']
    assert [g['strength'] for g in groups] == ['STRONG', 'MEDIUM', 'WEAK']
    assert [g['label'] for g in groups] == ['强', '中', '弱']
    # 强 3 项 / 中 2 项 / 弱 6 项（与截图一致）
    assert [len(g['items']) for g in groups] == [3, 2, 6]
    keys = {item['key'] for g in groups for item in g['items']}
    assert {'id_card', 'channel_uid', 'phone', 'email', 'work_experience'} <= keys


def test_catalog_items_carry_hint_for_tooltip(auth_client):
    resp = auth_client.get('/api/v1/duplicate-rules/catalog/')
    flat = {
        item['key']: item
        for g in resp.data['data']['groups']
        for item in g['items']
    }
    assert '公司名称、起止日期、职位名称完全一致' in flat['work_experience']['hint']


# ============================================================
# config
# ============================================================
def test_config_falls_back_to_defaults(auth_client):
    resp = auth_client.get('/api/v1/duplicate-rules/config/')
    assert resp.status_code == 200
    data = resp.data['data']
    assert data['merge']['enabled'] is True
    assert data['merge']['cancel_unaccepted_headhunter'] is True
    assert len(data['merge']['strategies']) == 3
    assert data['application']['enabled'] is True
    assert data['application']['window_months'] == 6


def test_config_patch_is_shallow_merge(auth_client):
    resp = auth_client.put(
        '/api/v1/duplicate-rules/config/',
        {'merge': {'enabled': False}},
        format='json',
    )
    assert resp.status_code == 200
    # 未提交的字段必须保留默认值，不能被整体覆盖清空
    assert resp.data['data']['merge']['enabled'] is False
    assert resp.data['data']['merge']['cancel_unaccepted_headhunter'] is True

    again = auth_client.get('/api/v1/duplicate-rules/config/')
    assert again.data['data']['merge']['enabled'] is False
    assert DuplicateConfig.objects.filter(key='merge').count() == 1


def test_config_patch_application_window(auth_client):
    resp = auth_client.put(
        '/api/v1/duplicate-rules/config/',
        {'application': {'enabled': False, 'window_months': 12}},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['data']['application']['window_months'] == 12
    assert resp.data['data']['application']['enabled'] is False


def test_config_rejects_unknown_key(auth_client):
    resp = auth_client.put(
        '/api/v1/duplicate-rules/config/',
        {'unknown': {}},
        format='json',
    )
    assert resp.status_code == 400
    assert 'unknown' in resp.data['message']


def test_config_rejects_empty_body(auth_client):
    resp = auth_client.put('/api/v1/duplicate-rules/config/', {}, format='json')
    assert resp.status_code == 400


# ============================================================
# rules：惰性种入
# ============================================================
def test_rules_are_seeded_lazily_with_system_defaults(auth_client):
    assert DuplicateRule.objects.count() == 0
    resp = auth_client.get(RULES_URL)
    assert resp.status_code == 200
    data = resp.data['data']
    assert len(data) == len(DEFAULT_RULES) == 5
    assert [r['name'] for r in data] == [spec['name'] for spec in DEFAULT_RULES]
    # 种子规则 = 2 条系统内置（不可删除）+ 3 条预置规则（可编辑/可删除）
    system_names = {spec['name'] for spec in DEFAULT_RULES if spec.get('is_system')}
    assert sum(1 for r in data if r['is_system']) == len(system_names)
    assert all((r['is_system'] is True) == (r['name'] in system_names) for r in data)


def test_seeding_is_idempotent(auth_client):
    auth_client.get(RULES_URL)
    auth_client.get(RULES_URL)
    assert DuplicateRule.objects.count() == len(DEFAULT_RULES)


def test_seeding_does_not_overwrite_user_changes(auth_client):
    auth_client.get(RULES_URL)
    rule = DuplicateRule.objects.get(name='基于身份证')
    rule.is_enabled = False
    rule.save(update_fields=['is_enabled'])

    auth_client.get(RULES_URL)
    rule.refresh_from_db()
    assert rule.is_enabled is False, '再次读取不得把用户停用状态覆盖回默认'


def test_seeded_rules_expose_condition_and_items_text(auth_client):
    resp = auth_client.get(RULES_URL)
    by_name = {r['name']: r for r in resp.data['data']}
    assert by_name['基于联系方式']['condition_text'] == '任意 2 项'
    assert by_name['基于联系方式']['items_text'] == ['手机号', '邮箱', '姓名']
    assert by_name['基于身份证']['condition_text'] == '全部'
    assert by_name['基于身份证']['items_text'] == ['证件号码']


# ============================================================
# rules：创建
# ============================================================
def test_create_custom_rule(auth_client):
    resp = auth_client.post(
        RULES_URL,
        {
            'name': '基于邮箱',
            'conditionLogic': 'ALL',
            'items': [{'key': 'email'}, {'key': 'name'}],
        },
        format='json',
    )
    assert resp.status_code == 201
    rule = DuplicateRule.objects.get(name='基于邮箱')
    assert rule.is_system is False
    assert rule.is_enabled is True
    # strength 由服务端 catalog 决定，客户端不传也不能为空
    assert rule.items == [
        {'key': 'email', 'strength': 'MEDIUM'},
        {'key': 'name', 'strength': 'WEAK'},
    ]


def test_create_rule_requires_at_least_one_strong_or_medium(auth_client):
    resp = auth_client.post(
        RULES_URL,
        {'name': '纯弱项规则', 'items': [{'key': 'name'}, {'key': 'gender'}]},
        format='json',
    )
    assert resp.status_code == 400
    assert '至少添加 1 项强查重项或中查重项' in str(resp.data)


def test_create_rule_rejects_unknown_item_key(auth_client):
    resp = auth_client.post(
        RULES_URL,
        {'name': '脏 key', 'items': [{'key': 'phone'}, {'key': 'not_a_field'}]},
        format='json',
    )
    assert resp.status_code == 400
    assert 'not_a_field' in str(resp.data)
    assert DuplicateRule.objects.filter(name='脏 key').count() == 0


def test_create_rule_rejects_empty_name(auth_client):
    resp = auth_client.post(
        RULES_URL,
        {'name': '   ', 'items': [{'key': 'phone'}]},
        format='json',
    )
    assert resp.status_code == 400


def test_any_count_cannot_exceed_selected_items(auth_client):
    resp = auth_client.post(
        RULES_URL,
        {
            'name': '任意 5 项',
            'conditionLogic': 'ANY',
            'anyCount': 5,
            'items': [{'key': 'phone'}, {'key': 'email'}],
        },
        format='json',
    )
    assert resp.status_code == 400


def test_any_rule_accepts_valid_count(auth_client):
    resp = auth_client.post(
        RULES_URL,
        {
            'name': '联系方式任一',
            'conditionLogic': 'ANY',
            'anyCount': 2,
            'items': [{'key': 'phone'}, {'key': 'email'}, {'key': 'name'}],
        },
        format='json',
    )
    assert resp.status_code == 201
    rule = DuplicateRule.objects.get(name='联系方式任一')
    assert rule.condition_logic == 'ANY'
    assert rule.any_count == 2


def test_all_logic_forces_any_count_to_one(auth_client):
    resp = auth_client.post(
        RULES_URL,
        {
            'name': '全项一致',
            'conditionLogic': 'ALL',
            'anyCount': 3,
            'items': [{'key': 'id_card'}],
        },
        format='json',
    )
    assert resp.status_code == 201
    assert DuplicateRule.objects.get(name='全项一致').any_count == 1


def test_duplicate_items_are_deduplicated(auth_client):
    resp = auth_client.post(
        RULES_URL,
        {'name': '重复项', 'items': [{'key': 'phone'}, {'key': 'phone'}]},
        format='json',
    )
    assert resp.status_code == 201
    assert DuplicateRule.objects.get(name='重复项').items == [
        {'key': 'phone', 'strength': 'MEDIUM'}
    ]


# ============================================================
# rules：更新 / 删除 / 启用
# ============================================================
def test_update_rule(auth_client):
    auth_client.get(RULES_URL)
    rule = DuplicateRule.objects.get(name='基于身份证')
    resp = auth_client.put(
        f'{RULES_URL}{rule.id}/',
        {'name': '基于身份证（改）', 'items': [{'key': 'id_card'}, {'key': 'phone'}]},
        format='json',
    )
    assert resp.status_code == 200
    rule.refresh_from_db()
    assert rule.name == '基于身份证（改）'
    assert [i['key'] for i in rule.items] == ['id_card', 'phone']


def test_update_rejects_removing_last_strong_medium_item(auth_client):
    auth_client.get(RULES_URL)
    rule = DuplicateRule.objects.get(name='基于身份证')
    resp = auth_client.put(
        f'{RULES_URL}{rule.id}/',
        {'items': [{'key': 'name'}]},
        format='json',
    )
    assert resp.status_code == 400
    rule.refresh_from_db()
    assert [i['key'] for i in rule.items] == ['id_card'], '校验失败不得落库'


def test_system_rule_cannot_be_deleted(auth_client):
    auth_client.get(RULES_URL)
    rule = DuplicateRule.objects.filter(is_system=True).first()
    resp = auth_client.delete(f'{RULES_URL}{rule.id}/')
    assert resp.status_code == 400
    assert '系统内置规则不可删除' in resp.data['message']
    assert DuplicateRule.objects.filter(pk=rule.pk).count() == 1


def test_custom_rule_is_soft_deleted(auth_client):
    auth_client.post(
        RULES_URL,
        {'name': '待删除规则', 'items': [{'key': 'phone'}]},
        format='json',
    )
    rule = DuplicateRule.objects.get(name='待删除规则')
    resp = auth_client.delete(f'{RULES_URL}{rule.id}/')
    assert resp.status_code == 200

    # 本项目 .objects 是默认管理器（不自动过滤软删），故显式按 deleted_at 断言
    assert DuplicateRule.objects.filter(pk=rule.pk, deleted_at__isnull=True).count() == 0
    raw = DuplicateRule.objects.get(pk=rule.pk)
    assert raw.deleted_at is not None, '必须是软删，不能物理删除'


def test_toggle_flips_and_accepts_explicit_value(auth_client):
    auth_client.get(RULES_URL)
    rule = DuplicateRule.objects.get(name='基于身份证')
    assert rule.is_enabled is True

    resp = auth_client.post(f'{RULES_URL}{rule.id}/toggle/', {}, format='json')
    assert resp.status_code == 200
    rule.refresh_from_db()
    assert rule.is_enabled is False

    # 前端发 camelCase（全局 parser 会下划线化）
    resp = auth_client.post(
        f'{RULES_URL}{rule.id}/toggle/', {'isEnabled': True}, format='json',
    )
    assert resp.status_code == 200
    rule.refresh_from_db()
    assert rule.is_enabled is True


def test_detail_404_for_missing_rule(auth_client):
    assert auth_client.get(f'{RULES_URL}999999/').status_code == 404


# ============================================================
# reset
# ============================================================
def test_reset_drops_custom_rules_and_restores_defaults(auth_client):
    auth_client.get(RULES_URL)
    auth_client.post(
        RULES_URL,
        {'name': '自定义规则 X', 'items': [{'key': 'phone'}]},
        format='json',
    )
    # 把系统规则改坏，reset 后必须复位
    rule = DuplicateRule.objects.get(name='基于身份证')
    rule.items = [{'key': 'phone', 'strength': 'MEDIUM'}]
    rule.is_enabled = False
    rule.save(update_fields=['items', 'is_enabled'])

    resp = auth_client.post(f'{RULES_URL}reset/', {}, format='json')
    assert resp.status_code == 200

    alive = DuplicateRule.objects.filter(deleted_at__isnull=True)
    assert alive.filter(name='自定义规则 X').count() == 0
    assert alive.count() == len(DEFAULT_RULES)
    restored = alive.get(name='基于身份证')
    assert [i['key'] for i in restored.items] == ['id_card']
    assert restored.is_enabled is True
    # 默认停用的那条保持停用（与截图一致）
    assert alive.get(name='基于工作经历（系统）').is_enabled is False
    # 自定义规则是软删，不是物理删
    assert DuplicateRule.objects.filter(name='自定义规则 X').count() == 1


# ============================================================
# 认证 + camelCase 边界
# ============================================================
def test_endpoints_require_authentication(api_client):
    assert api_client.get(RULES_URL).status_code in (401, 403)
    assert api_client.get('/api/v1/duplicate-rules/catalog/').status_code in (401, 403)
    assert api_client.get('/api/v1/duplicate-rules/config/').status_code in (401, 403)


def test_response_json_keys_are_camel_case(auth_client):
    """FE 直接消费 JSON 文本，故必须断言渲染后的键名（resp.data 是预渲染的 snake_case）。"""
    auth_client.get(RULES_URL)
    resp = auth_client.get(RULES_URL)
    payload = json.loads(resp.content)

    first = payload['data'][0]
    for camel_key in (
        'isSystem', 'conditionLogic', 'anyCount', 'isEnabled',
        'orderIndex', 'conditionText', 'itemsText',
    ):
        assert camel_key in first, f'响应缺少 camelCase 键 {camel_key}'
    for snake_key in ('is_system', 'condition_logic', 'is_enabled'):
        assert snake_key not in first, f'响应泄漏 snake_case 键 {snake_key}'


def test_camel_case_request_is_parsed_into_snake_case_fields(auth_client):
    resp = auth_client.post(
        RULES_URL,
        {
            'name': '驼峰入参规则',
            'conditionLogic': 'ANY',
            'anyCount': 2,
            'isEnabled': False,
            'orderIndex': 77,
            'items': [{'key': 'phone'}, {'key': 'email'}, {'key': 'name'}],
        },
        format='json',
    )
    assert resp.status_code == 201
    rule = DuplicateRule.objects.get(name='驼峰入参规则')
    assert rule.condition_logic == 'ANY'
    assert rule.any_count == 2
    assert rule.is_enabled is False
    assert rule.order_index == 77


def test_config_json_dict_keys_are_camelized_on_output(auth_client):
    """自由 JSON dict 的键同样会被递归驼峰化 —— 前端契约依赖这一点，显式守住。"""
    resp = auth_client.get('/api/v1/duplicate-rules/config/')
    payload = json.loads(resp.content)
    merge = payload['data']['merge']
    assert 'cancelUnacceptedHeadhunter' in merge
    assert 'cancel_unaccepted_headhunter' not in merge
    assert 'windowMonths' in payload['data']['application']
