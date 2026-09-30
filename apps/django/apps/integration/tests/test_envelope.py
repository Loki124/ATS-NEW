"""Batch 12 — BackgroundCheckOrderViewSet 信封契约锁定。

覆盖范围（仅锁定本批实际改动/受影响的端点）：
- list    : 经 StandardResultsSetPagination → {success, data:[...], pagination, ...}
- retrieve: 经 EnvelopeWriteMixin          → {success, data:{...}, message, code}

说明：cancel / query / report 为自定义 @action，已各自返回手动
{success, message, data} 形状（失败分支需 success=False，success_response 无法表达），
本批不改、亦不破坏前端 r.success / r.message 契约，故不在此重复锁定。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.integration.services import create_background_check_order

BASE = '/api/v1/background-check/orders'


def _assert_envelope(body):
    assert body.get('success') is True
    assert 'data' in body
    assert body.get('code') == 0


@pytest.fixture
def super_client(db):
    U = get_user_model()
    user = U.objects.create_superuser('bg_super', 'BgSuper123!')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def order(bg_config):
    return create_background_check_order(
        config=bg_config, candidate_id='c_env', items=[], order_number='ENV-1',
    )


def test_list_envelope(super_client, order):
    resp = super_client.get(f'{BASE}/')
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], list)
    assert any(o['id'] == order.id for o in body['data'])


def test_retrieve_envelope(super_client, order):
    resp = super_client.get(f'{BASE}/{order.id}/')
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], dict)
    assert body['data']['id'] == order.id
    # 详情序列化器含 events（BackgroundCheckOrderDetailSerializer）
    assert 'events' in body['data']


def test_retrieve_not_raw(super_client, order):
    """反向契约：retrieve 必须是信封，裸 DRF 默认会把订单字段直接铺在顶层。"""
    body = super_client.get(f'{BASE}/{order.id}/').json()
    assert 'order_number' not in body              # 原始 snake 字段不在顶层
    assert 'orderNumber' not in body               # 驼峰字段也不在顶层（在 data 内）
    assert body['data']['orderNumber'] == order.order_number
