"""T6 供应商适配器抽象契约测试。

定义离线 MockSupplier（不触发任何网络），覆盖 create/cancel/query_order/query_products/
fetch_report 五个抽象方法 + to_canonical_status 映射。
"""
import time

from apps.integration.models import BGOrderStatus
from apps.integration.suppliers.base import (
    BackgroundCheckResult,
    BaseBackgroundCheckSupplier,
    CreateOrderRequest,
)


class MockSupplier(BaseBackgroundCheckSupplier):
    """离线 Mock 适配器：绕过网络初始化，返回固定罐头数据。"""

    def __init__(self, config=None):
        # 仅设置 services 层读取的少量属性，不解析真实 config / 不发起网络
        self._config = config
        self._cfg = {}
        self._secret = {}
        self._app_id = 'mock'
        self._app_key = 'mock'
        self._base_url = 'https://mock.local'

    def create_order(self, req):
        return BackgroundCheckResult(
            success=True, message='OK',
            data={'code': 0, 'message': 'success', 'data': {'number': 'MOCK-N1'}},
            duration_ms=5,
        )

    def cancel_order(self, order_number):
        return BackgroundCheckResult(
            success=True, message='OK',
            data={'code': 0, 'data': {'number': order_number, 'cancelled': True}},
            duration_ms=5,
        )

    def query_order(self, order_number):
        return BackgroundCheckResult(
            success=True, message='OK',
            data={
                'order_number': order_number,
                'status': 3,
                'statusName': '背调中',
                'riskLevel': 2,
                'reportUrl': 'https://mock.local/r.pdf',
                'completionTime': int(time.time() * 1000),
            },
            duration_ms=5,
        )

    def query_products(self, product_token=None):
        return BackgroundCheckResult(
            success=True, message='OK',
            data={
                'list': [{
                    'productToken': 'pkg1',
                    'productName': '基础背调',
                    'price': 29900,
                    'deliverDays': 3,
                    'projectName': '身份验证；学历验证',
                    'remark': '',
                }],
                'pagination': {'page': 1, 'pageSize': 20, 'total': 1},
            },
            duration_ms=5,
        )

    def fetch_report(self, order):
        return BackgroundCheckResult(
            success=True, message='OK',
            data={
                'report_url': 'https://mock.local/r.pdf',
                'content_type': 'application/pdf',
                'fetched_at': int(time.time() * 1000),
                'size': 1024,
            },
            duration_ms=5,
        )


def test_create_returns_canned_number():
    s = MockSupplier()
    res = s.create_order(CreateOrderRequest(candidate_id='c', items=['id']))
    assert res.success is True
    assert (res.data or {}).get('data', {}).get('number') == 'MOCK-N1'


def test_cancel_ok():
    s = MockSupplier()
    res = s.cancel_order('O1')
    assert res.success is True
    assert (res.data or {}).get('data', {}).get('cancelled') is True


def test_query_order_canned_status():
    s = MockSupplier()
    res = s.query_order('O1')
    assert res.success is True
    assert res.data['status'] == 3


def test_query_products_canned_list():
    s = MockSupplier()
    res = s.query_products()
    assert res.success is True
    lst = (res.data or {}).get('list') or []
    assert len(lst) == 1 and lst[0]['productToken'] == 'pkg1'


def test_fetch_report_canned():
    s = MockSupplier()

    class _Order:
        report_url = 'https://mock.local/r.pdf'

    res = s.fetch_report(_Order())
    assert res.success is True
    assert res.data['size'] == 1024


def test_to_canonical_status_identity():
    s = MockSupplier()
    assert s.to_canonical_status(3) == 3
    assert s.to_canonical_status(BGOrderStatus.COMPLETED) == BGOrderStatus.COMPLETED
