"""tip + default_talent_pool 字段：落库与序列化输出穿透测试 (2026-10-13).

走真实 HTTP 端点 (wizard/save + 详情 GET), 验证:
- wizard 保存把 tip / default_talent_pool 写进 SceneRule 行 (落库核验);
- 详情序列化输出含 tip / default_talent_pool;
- 非法 default_talent_pool 被服务层归一化为 '' (不落脏数据);
- 空值可正常保存。
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


def _wizard_url(rule_id: str) -> str:
    return f'/api/v1/reason-library/rules/{rule_id}/wizard/save/'


def _payload(rule, reason_tag, **overrides):
    p = {
        'name': rule.name,
        'description': rule.description,
        'enabled': True,
        'categories': [
            {
                'clientId': 'cat-a',
                'parentClientId': None,
                'name': '分类A',
                'order': 1,
                'allowCustom': False,
                'tagIds': [reason_tag.id],
            },
        ],
        'scenes': ['取消面试'],
        'tip': '',
        'default_talent_pool': '',
    }
    p.update(overrides)
    return p


def test_wizard_save_persists_tip_and_default_talent_pool(admin_api_client, custom_rule, reason_tag):
    """wizard 保存: tip + default_talent_pool 落库且回显。"""
    client, _ = admin_api_client
    payload = _payload(
        custom_rule, reason_tag,
        tip='请如实填写详细原因，便于后续复盘',
        default_talent_pool='ACTIVE',
    )
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 200, resp.json()
    data = resp.json()['data']
    # 输出含字段 (前端契约走 camelCase 别名 defaultTalentPool)
    assert data.get('tip') == '请如实填写详细原因，便于后续复盘'
    assert data.get('defaultTalentPool') == 'ACTIVE'
    # 落库核验
    custom_rule.refresh_from_db()
    assert custom_rule.tip == '请如实填写详细原因，便于后续复盘'
    assert custom_rule.default_talent_pool == 'ACTIVE'


def test_wizard_save_invalid_talent_pool_normalized_to_empty(admin_api_client, custom_rule, reason_tag):
    """非法人才库 key 被服务层归一化为 '' (不落脏数据)。"""
    client, _ = admin_api_client
    payload = _payload(
        custom_rule, reason_tag,
        tip='提示X',
        default_talent_pool='NOT_A_POOL',
    )
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 200, resp.json()
    data = resp.json()['data']
    assert data.get('defaultTalentPool') == ''
    custom_rule.refresh_from_db()
    assert custom_rule.default_talent_pool == ''


def test_wizard_save_blank_fields_ok(admin_api_client, custom_rule, reason_tag):
    """空 tip / 空 default_talent_pool 可正常保存。"""
    client, _ = admin_api_client
    payload = _payload(custom_rule, reason_tag, tip='', default_talent_pool='')
    resp = client.post(_wizard_url(custom_rule.id), payload, format='json')
    assert resp.status_code == 200, resp.json()
    custom_rule.refresh_from_db()
    assert custom_rule.tip == ''
    assert custom_rule.default_talent_pool == ''


def test_rule_detail_serializer_exposes_fields(admin_api_client, custom_rule):
    """详情序列化输出含 tip / default_talent_pool (camelCase 别名 defaultTalentPool 同步)。"""
    custom_rule.tip = '直接设置的提示'
    custom_rule.default_talent_pool = 'GENERAL'
    custom_rule.save(update_fields=['tip', 'default_talent_pool', 'updated_at'])
    client, _ = admin_api_client
    resp = client.get(f'/api/v1/reason-library/rules/{custom_rule.id}/')
    assert resp.status_code == 200, resp.json()
    data = resp.json()['data']
    assert data.get('tip') == '直接设置的提示'
    assert data.get('defaultTalentPool') == 'GENERAL'
