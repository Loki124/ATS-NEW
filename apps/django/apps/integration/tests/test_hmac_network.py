"""T6 真实网络方法测试（离线，mock requests）。

覆盖 HmacBackgroundCheckSupplier 经 requests 发起的 6 个方法：
create_order / cancel_order / query_order / query_products / fetch_report / health。
验证成功判定、HTTP 码分支、响应归一化、无 URL 早退、签名头随请求发出。
"""
import socket
from unittest.mock import patch

from apps.integration.suppliers.base import CreateOrderRequest
from apps.integration.suppliers.hmac_adapter import HmacBackgroundCheckSupplier

# 2026-10-08 (#15): fetch_report 经 ssrf_safe_get 发起, 会先解析目标主机 DNS 以判定内网。
# 离线测试用这个桩把任意主机解析到公网 IP, 避免真实 DNS (sp.test 不可解析 → 误判内网)。
_PUBLIC_DNS = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 0))]


class _Resp:
    """最小 requests.Response 桩。"""
    def __init__(self, status_code=200, json_data=None, content=b'', headers=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.content = content
        self.headers = headers or {'Content-Type': 'application/json'}

    def json(self):
        return self._json


def _make_supplier(base_url='https://sp.test'):
    s = HmacBackgroundCheckSupplier.__new__(HmacBackgroundCheckSupplier)
    s._app_id = 'sp_test'
    s._app_key = 'testkey'
    s._base_url = base_url
    return s


# ---------------------------------------------------------- create_order
@patch('apps.integration.suppliers.hmac_adapter.requests.post')
def test_create_order_accepts_201(mock_post):
    mock_post.return_value = _Resp(201, {'code': 0, 'data': {'number': 'X1'}})
    s = _make_supplier()
    res = s.create_order(CreateOrderRequest(request_id='R1', candidate_id='C1', items=['edu', 'work']))
    assert res.success is True
    args, kwargs = mock_post.call_args
    # 请求体含业务字段，且签名头随请求发出
    assert kwargs['json']['requestId'] == 'R1'
    assert kwargs['json']['items'] == ['edu', 'work']
    assert kwargs['headers']['X-App-Id'] == 'sp_test'
    assert 'X-App-Sign' in kwargs['headers']


@patch('apps.integration.suppliers.hmac_adapter.requests.post')
def test_create_order_5xx_fails(mock_post):
    mock_post.return_value = _Resp(500, {'code': 50001})
    s = _make_supplier()
    res = s.create_order(CreateOrderRequest(candidate_id='C1', items=[]))
    assert res.success is False
    assert '500' in res.message


@patch('apps.integration.suppliers.hmac_adapter.requests.post')
def test_create_order_request_exception_fails(mock_post):
    import requests
    mock_post.side_effect = requests.RequestException('conn reset')
    s = _make_supplier()
    res = s.create_order(CreateOrderRequest(candidate_id='C1', items=[]))
    assert res.success is False
    assert '请求异常' in res.message


# ---------------------------------------------------------- cancel_order
@patch('apps.integration.suppliers.hmac_adapter.requests.post')
def test_cancel_requires_200_and_code(mock_post):
    s = _make_supplier()
    # 200 + code 0 → 成功
    mock_post.return_value = _Resp(200, {'code': 0})
    assert s.cancel_order('O1').success is True
    # 201 + code 0 → 失败（规范仅 200 承载业务结果，不接受 201）
    mock_post.return_value = _Resp(201, {'code': 0})
    assert s.cancel_order('O1').success is False
    # 200 + 非 0 code → 失败（如 409 已取消）
    mock_post.return_value = _Resp(200, {'code': 40901})
    assert s.cancel_order('O1').success is False


# ---------------------------------------------------------- query_order
@patch('apps.integration.suppliers.hmac_adapter.requests.get')
def test_query_order_normalizes_status(mock_get):
    # 响应信封 data 即为订单详情对象（adapter 取 envelope['data'] 作为 inner）
    mock_get.return_value = _Resp(200, {
        'code': 0,
        'data': {
            'status': 3, 'statusName': '背调中', 'riskLevel': 2,
            'reportUrl': 'https://sp.test/r.pdf', 'completionTime': 123,
        },
    })
    s = _make_supplier()
    res = s.query_order('O1')
    assert res.success is True
    assert res.data['status'] == 3
    assert res.data['reportUrl'] == 'https://sp.test/r.pdf'


@patch('apps.integration.suppliers.hmac_adapter.requests.get')
def test_query_order_non_200_fails(mock_get):
    mock_get.return_value = _Resp(404, {'code': 40401})
    s = _make_supplier()
    res = s.query_order('O1')
    assert res.success is False


# ---------------------------------------------------------- query_products
@patch('apps.integration.suppliers.hmac_adapter.requests.get')
def test_query_products_returns_list(mock_get):
    mock_get.return_value = _Resp(200, {'code': 0, 'data': {'list': [{'productToken': 'p1'}]}})
    s = _make_supplier()
    res = s.query_products()
    assert res.success is True
    assert (res.data or {}).get('data', {}).get('list', [])[0]['productToken'] == 'p1'


@patch('apps.integration.suppliers.hmac_adapter.requests.get')
def test_query_products_with_token_query(mock_get):
    mock_get.return_value = _Resp(200, {'code': 0, 'data': {'list': []}})
    s = _make_supplier()
    s.query_products(product_token='pkg1')
    args, kwargs = mock_get.call_args
    assert kwargs['params'].get('productToken') == 'pkg1'


# ---------------------------------------------------------- fetch_report
@patch('apps.integration.ssrf.socket.getaddrinfo', return_value=_PUBLIC_DNS)
@patch('apps.integration.suppliers.hmac_adapter.requests.get')
def test_fetch_report_ok(mock_get, _mock_dns):
    mock_get.return_value = _Resp(200, content=b'PDF-BYTES', headers={'Content-Type': 'application/pdf'})
    s = _make_supplier()

    class _Order:
        report_url = 'https://sp.test/report.pdf'

    res = s.fetch_report(_Order())
    assert res.success is True
    assert res.data['content_type'] == 'application/pdf'
    assert res.data['size'] == len(b'PDF-BYTES')


def test_fetch_report_no_url_fails_without_network():
    s = _make_supplier()

    class _Order:
        report_url = ''

    res = s.fetch_report(_Order())
    assert res.success is False
    assert '报告地址' in res.message


# ---------------------------------------------------------- health
def test_health_no_base_url_fails_without_network():
    s = _make_supplier(base_url='')
    res = s.health()
    assert res.success is False
    assert 'BaseURL' in res.message


@patch('apps.integration.suppliers.hmac_adapter.requests.get')
def test_health_ok(mock_get):
    mock_get.return_value = _Resp(200, {'code': 0, 'data': {'status': 'up'}})
    s = _make_supplier()
    res = s.health()
    assert res.success is True
