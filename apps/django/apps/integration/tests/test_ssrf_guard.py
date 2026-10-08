"""SSRF 防护测试 (2026-10-08 审查 #15 / F-15).

核心: `ssrf_safe_get` 必须拒绝内网/保留段/云元数据/非法协议, 放行公网 https,
且重定向每一跳都要再校验。用 mock 隔离真实网络与 DNS。
"""
import socket
from unittest import mock

import pytest
import requests

from apps.integration.ssrf import host_blocked, ssrf_safe_get


def _fake_getaddrinfo(ips):
    """构造 socket.getaddrinfo 返回值: 每个 ip 一个 (family, type, proto, canon, (ip, port))。"""
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 0)) for ip in ips]


class _FakeResp:
    def __init__(self, status_code=200, headers=None, content=b'x'):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content


# ---- host_blocked: 命中内网/保留段 ----

@pytest.mark.parametrize('host', [
    '127.0.0.1', '127.0.0.2',
    '10.0.0.5', '10.255.255.255',
    '172.16.0.1', '172.31.255.255',
    '192.168.1.1', '192.168.0.254',
    '169.254.169.254',            # 云元数据
    '169.254.1.1',                # 链路本地
    '0.0.0.0',
    'localhost',                  # 解析到 127.0.0.1
    '::1',                        # IPv6 环回
    'fd00::1',                    # ULA
    'fe80::1',                    # 链路本地
])
def test_host_blocked_rejects_internal(host):
    with mock.patch('apps.integration.ssrf.socket.getaddrinfo',
                    return_value=_fake_getaddrinfo([host if ':' not in host else '127.0.0.1'])):
        # localhost / ::1 用字面量走 _addr_blocked; 这里主要验域名解析路径
        assert host_blocked(host) is True


def test_host_blocked_allows_public_ip():
    assert host_blocked('93.184.216.34') is False     # example.com 公网 IP


def test_host_blocked_allows_public_domain():
    with mock.patch('apps.integration.ssrf.socket.getaddrinfo',
                    return_value=_fake_getaddrinfo(['93.184.216.34'])):
        assert host_blocked('example.com') is False


def test_host_blocked_rejects_if_any_resolved_ip_internal():
    # DNS 返回公网 + 内网两笔, 任一内网即拒绝 (防 DNS 同时解析暴露)
    with mock.patch('apps.integration.ssrf.socket.getaddrinfo',
                    return_value=_fake_getaddrinfo(['93.184.216.34', '10.0.0.9'])):
        assert host_blocked('evil.example.com') is True


# ---- ssrf_safe_get: 协议 / 主机 / 重定向 ----

def test_rejects_non_http_scheme():
    with pytest.raises(ValueError):
        ssrf_safe_get('file:///etc/passwd')
    with pytest.raises(ValueError):
        ssrf_safe_get('ftp://example.com/x')
    with pytest.raises(ValueError):
        ssrf_safe_get('gopher://127.0.0.1:6379/_')


def test_rejects_internal_host_without_request():
    # host_blocked 命中即抛, requests 不应被调用
    with mock.patch('apps.integration.ssrf.requests.get') as m_get, \
         mock.patch('apps.integration.ssrf.socket.getaddrinfo',
                    return_value=_fake_getaddrinfo(['169.254.169.254'])):
        with pytest.raises(ValueError):
            ssrf_safe_get('http://169.254.169.254/latest/meta-data/')
        m_get.assert_not_called()


def test_allows_public_https_and_returns_resp():
    fake = _FakeResp(200)
    with mock.patch('apps.integration.ssrf.requests.get', return_value=fake) as m_get, \
         mock.patch('apps.integration.ssrf.socket.getaddrinfo',
                    return_value=_fake_getaddrinfo(['93.184.216.34'])):
        resp = ssrf_safe_get('https://public.example.com/report.pdf', timeout=10)
        assert resp is fake
        m_get.assert_called_once()


def test_allowed_hosts_whitelist_enforced():
    with mock.patch('apps.integration.ssrf.requests.get') as m_get:
        with pytest.raises(ValueError):
            ssrf_safe_get('https://other.example.org/x', allowed_hosts={'trusted.com'})
        m_get.assert_not_called()


def test_redirect_to_internal_is_rejected():
    # 首跳公网, 二跳指向内网 → 必须拒绝且不再请求第二跳
    public = _FakeResp(302, headers={'Location': 'http://127.0.0.1:9000/secret'})
    calls = []

    def _get(url, **kw):
        calls.append(url)
        if url.startswith('http://127.0.0.1'):
            return _FakeResp(200)
        return public

    with mock.patch('apps.integration.ssrf.requests.get', side_effect=_get), \
         mock.patch('apps.integration.ssrf.socket.getaddrinfo',
                    return_value=_fake_getaddrinfo(['93.184.216.34'])), pytest.raises(ValueError):
        ssrf_safe_get('http://public.example.com/r', timeout=10)
    # 只发了首跳, 内网二跳未发
    assert calls == ['http://public.example.com/r']


def test_fetch_report_blocks_internal_url():
    """端到端: adapter.fetch_report 遇到内网 report_url 必须返回 success=False, 不抛、不请求。"""
    from apps.integration.models import BackgroundCheckOrder
    from apps.integration.suppliers.hmac_adapter import HmacBackgroundCheckSupplier

    # fetch_report 不依赖 supplier 配置, 用最小桩子类绕开工厂构造
    class _Stub(HmacBackgroundCheckSupplier):
        def __init__(self):  # noqa: D401
            pass

    order = BackgroundCheckOrder()
    order.report_url = 'http://169.254.169.254/latest/meta-data/'

    supplier = _Stub()
    with mock.patch('apps.integration.ssrf.socket.getaddrinfo',
                    return_value=_fake_getaddrinfo(['169.254.169.254'])):
        res = supplier.fetch_report(order)
    assert res.success is False
    assert 'SSRF' in res.message or '内网' in res.message or '保留段' in res.message
