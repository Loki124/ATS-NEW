"""T6 services 层委托测试。

monkeypatch ``services.get_supplier`` 返回离线 MockSupplier，验证：
- request/cancel/test_connection 正确委托到适配器并落 IntegrationSyncLog
- query_background_check_order / fetch_background_check_report 包裹适配器结果
"""
import pytest

from apps.integration import services
from apps.integration.models import (
    BackgroundCheckOrder,
    BGOrderStatus,
    IntegrationSyncLog,
)
from apps.integration.tests.test_adapter import MockSupplier


@pytest.fixture
def mock_supplier(monkeypatch):
    inst = MockSupplier(None)
    monkeypatch.setattr(services, 'get_supplier', lambda config: inst)
    return inst


def test_request_delegates_and_logs(bg_config, mock_supplier):
    res = services.request_background_check('cand1', ['id', 'edu'], config_id=bg_config.id)
    assert res['success'] is True
    assert IntegrationSyncLog.objects.filter(config=bg_config, sync_type='CREATE_ORDER').exists()
    assert BackgroundCheckOrder.objects.filter(order_number='MOCK-N1').exists()


def test_cancel_delegates_and_logs(bg_config, mock_supplier):
    order = BackgroundCheckOrder.objects.create(
        config=bg_config, order_number='O1', candidate_id='c', status=BGOrderStatus.ACCEPTED,
    )
    res = services.cancel_background_check_order(order)
    assert res['success'] is True
    assert IntegrationSyncLog.objects.filter(config=bg_config, sync_type='CANCEL_ORDER').exists()
    order.refresh_from_db()
    assert order.status == BGOrderStatus.CANCELLED


def test_test_connection_delegates(bg_config, mock_supplier):
    res = services.test_background_check_connection(bg_config)
    assert res['success'] is True
    assert IntegrationSyncLog.objects.filter(config=bg_config, sync_type='TEST_CONNECTION').exists()


def test_query_order_wraps(bg_config, mock_supplier):
    res = services.query_background_check_order('O1', config_id=bg_config.id)
    assert res['success'] is True
    assert res['data']['status'] == 3
    assert IntegrationSyncLog.objects.filter(sync_type='QUERY_ORDER').exists()


def test_fetch_report_wraps(bg_config, mock_supplier):
    order = BackgroundCheckOrder.objects.create(
        config=bg_config, order_number='O2', candidate_id='c',
        report_url='https://mock.local/r.pdf', status=BGOrderStatus.COMPLETED,
    )
    res = services.fetch_background_check_report(order)
    assert res['success'] is True
    assert res['data']['size'] == 1024
    assert IntegrationSyncLog.objects.filter(sync_type='FETCH_REPORT').exists()
