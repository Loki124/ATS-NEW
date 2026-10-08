"""T7 「发起背调」视图层端到端锁定（DRF 真实请求链路，MockSupplier 不触网）。

覆盖本次新增的三条端点 + 权限闸门：
- GET  /background-check/orders/suppliers/      → 列出启用中的背调供应商
- GET  /background-check/orders/products/       → 拉取套餐/查项（缺 config_id→400, 不存在→404）
- POST /background-check/orders/create-order/   → 发起背调（缺 candidate_id→400, 成功→落库 MOCK-N1）
- 权限：非 HR 角色（如普通员工）→ 403；HR/HRBP/超管 → 200
"""
import pytest
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient

from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.integration import services
from apps.integration import views
from apps.integration.models import BackgroundCheckOrder
from apps.integration.tests.test_adapter import MockSupplier


BASE = '/api/v1/background-check/orders'


@pytest.fixture
def mock_supplier(monkeypatch):
    inst = MockSupplier(None)
    # views.py 用 ``from .services import get_supplier`` 绑定到本模块命名空间，
    # 故需同时打掉 services 与 views 两处引用（create-order 走 services 内部，
    # products 走 views 直接调用）。
    monkeypatch.setattr(services, 'get_supplier', lambda config: inst)
    monkeypatch.setattr(views, 'get_supplier', lambda config: inst)
    return inst


@pytest.fixture
def hr_user(db):
    U = get_user_model()
    user = U.objects.create_user('bg_hr', password='x')
    RoleV2.objects.get_or_create(
        role_code='HR', system_code='recruit',
        defaults={'role_code': 'HR', 'system_code': 'recruit', 'status': 1},
    )
    UserRoleV2.objects.create(user_id=user.pk, role_code='HR', system_code='recruit')
    return user


@pytest.fixture
def plain_user(db):
    U = get_user_model()
    return U.objects.create_user('bg_plain', password='x')


@pytest.fixture
def hr_client(hr_user):
    c = APIClient()
    c.force_authenticate(user=hr_user)
    return c


@pytest.fixture
def plain_client(plain_user):
    c = APIClient()
    c.force_authenticate(user=plain_user)
    return c


# ===================== suppliers =====================

def test_suppliers_lists_active_bgc(hr_client, bg_config):
    resp = hr_client.get(f'{BASE}/suppliers/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    ids = [s['id'] for s in body['data']]
    assert bg_config.id in ids


def test_suppliers_forbidden_for_plain(plain_client, bg_config):
    resp = plain_client.get(f'{BASE}/suppliers/')
    assert resp.status_code in (401, 403)


# ===================== products =====================

def test_products_ok(hr_client, bg_config, mock_supplier):
    resp = hr_client.get(f'{BASE}/products/', {'config_id': bg_config.id})
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert 'list' in body['data']


def test_products_missing_config_id(hr_client, bg_config):
    resp = hr_client.get(f'{BASE}/products/')
    assert resp.status_code == 400


def test_products_unknown_config(hr_client):
    resp = hr_client.get(f'{BASE}/products/', {'config_id': 'no-such-config'})
    assert resp.status_code == 404


# ===================== create-order =====================

def test_create_order_ok(hr_client, bg_config, mock_supplier):
    payload = {
        'candidate_id': 'cand-xyz',
        'config_id': bg_config.id,
        'items': ['id', 'edu'],
        'candidate_name': '张三',
        'phone': '13800000000',
        'operator_name': '李四',
        'operator_phone': '13900000000',
    }
    resp = hr_client.post(f'{BASE}/create-order/', payload, format='json')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert BackgroundCheckOrder.objects.filter(order_number='MOCK-N1').exists()
    order = BackgroundCheckOrder.objects.get(order_number='MOCK-N1')
    assert order.candidate_id == 'cand-xyz'
    assert order.candidate_name == '张三'


def test_create_order_minimal_payload(hr_client, bg_config, mock_supplier):
    """仅传候选人与套餐，operator 信息缺省（发往供应商，不持久化到订单模型）。"""
    payload = {
        'candidate_id': 'cand-op',
        'config_id': bg_config.id,
        'items': ['id'],
    }
    resp = hr_client.post(f'{BASE}/create-order/', payload, format='json')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    order = BackgroundCheckOrder.objects.get(order_number='MOCK-N1')
    assert order.candidate_id == 'cand-op'
    # 未传 candidate_name → 落库空串
    assert order.candidate_name == ''


def test_create_order_missing_candidate_id(hr_client, bg_config, mock_supplier):
    resp = hr_client.post(
        f'{BASE}/create-order/',
        {'config_id': bg_config.id, 'items': ['id']},
        format='json',
    )
    assert resp.status_code == 400


def test_create_order_unknown_config(hr_client):
    resp = hr_client.post(
        f'{BASE}/create-order/',
        {'candidate_id': 'c1', 'config_id': 'no-such', 'items': ['id']},
        format='json',
    )
    assert resp.status_code == 400
    assert resp.json()['success'] is False


def test_create_order_forbidden_for_plain(plain_client, bg_config, mock_supplier):
    resp = plain_client.post(
        f'{BASE}/create-order/',
        {'candidate_id': 'c1', 'config_id': bg_config.id, 'items': ['id']},
        format='json',
    )
    assert resp.status_code in (401, 403)
