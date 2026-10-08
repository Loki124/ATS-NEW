"""SSRF 防护 —— 背调报告服务端拉取的安全 GET.

背景 (2026-10-08 审查 #15 / F-15):
    `hmac_adapter.fetch_report` 用 `requests.get(order.report_url)` 在服务端主动拉取背调报告。
    `report_url` 有两个来源:
      1. 操作员「已有报告」上传接口 (`integration/views.py`) —— 任意登录 HR 可填任意 URL;
      2. 供应商回调 `reportUrl` (`integration/services.py`) —— 供应商完全可控。
    不校验则攻击者/恶意供应商可令服务端请求 `http://169.254.169.254/latest/meta-data/`
    (云元数据, 拿临时凭据)、`http://127.0.0.1:6379/`(内网服务)、`http://10.x` 等,
    形成服务端请求伪造 (SSRF)。

防护:
    - 仅允许 http/https;
    - 解析目标主机, 命中内网 / 链路本地 / 保留段 / 云元数据 (169.254.169.254) 即拒绝;
    - 可选 `allowed_hosts` 白名单 (建议配置供应商域名, 见 settings.BG_REPORT_ALLOWED_HOSTS);
    - 不自动跟随重定向, 每一跳再次做同样的校验 (最多 max_redirects 跳)。

残留风险 (防御纵深): 本函数在校验时解析主机, `requests.get` 解析时可能拿到不同 IP
(DNS rebinding / TOCTOU)。缓解: 校验覆盖该主机**所有** A/AAAA 记录; 彻底消除需在出口网络
层做白名单 (allowed_hosts 或防火墙), 那才是 SSRF 的强控制。本项目视 allowed_hosts 为推荐补充。
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests

# 禁止的目标网络 (IPv4 + IPv6 + IPv4-mapped)。含 169.254.0.0/16 覆盖云元数据 169.254.169.254。
_BLOCKED_CIDRS = (
    '0.0.0.0/8',        # 本网络
    '10.0.0.0/8',       # 私网
    '127.0.0.0/8',      # 环回
    '169.254.0.0/16',   # 链路本地 + 云元数据
    '172.16.0.0/12',    # 私网
    '192.168.0.0/16',   # 私网
    '100.64.0.0/10',    # CGNAT
    '::1/128',          # IPv6 环回
    'fc00::/7',         # IPv6 ULA
    'fe80::/10',        # IPv6 链路本地
    '::ffff:0:0/96',    # IPv4-mapped (按 IPv4 再判)
)


def _blocked_networks():
    return [ipaddress.ip_network(c) for c in _BLOCKED_CIDRS]


def _addr_blocked(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    for net in _blocked_networks():
        if addr in net:
            return True
    return False


def host_blocked(host: str) -> bool:
    """主机 (字面量 IP 或域名) 是否命中内网/保留段。"""
    host = (host or '').strip().lower()
    if not host:
        return True
    # 1) 字面量 IP: 直接判定
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return _addr_blocked(host)
    # 2) 域名: 解析所有 A/AAAA 记录, 任一命中即拒绝
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True  # 解析不了 → 视为可疑, 拒绝
    for info in infos:
        if _addr_blocked(info[4][0]):
            return True
    return False


def ssrf_safe_get(
    url: str,
    timeout: int = 15,
    allowed_hosts=None,
    max_redirects: int = 3,
):
    """SSRF 安全的 GET。失败时抛 ``ValueError`` (由调用方转为拉取失败, 绝不发起请求)。"""
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f'不允许的协议: {parsed.scheme or "(空)"}')
    host = (parsed.hostname or '').lower()
    if not host:
        raise ValueError('缺少主机名')
    if allowed_hosts is not None and host not in set(allowed_hosts):
        raise ValueError(f'主机不在允许名单: {host}')
    if host_blocked(host):
        raise ValueError(f'目标地址命中内网/保留段: {host}')

    resp = requests.get(url, timeout=timeout, allow_redirects=False)
    seen = 0
    while 300 <= resp.status_code < 400 and resp.headers.get('Location'):
        if seen >= max_redirects:
            raise ValueError('重定向次数过多')
        loc = urljoin(url, resp.headers['Location'])
        p = urlparse(loc)
        h = (p.hostname or '').lower()
        if p.scheme not in ('http', 'https') or host_blocked(h) \
                or (allowed_hosts is not None and h not in set(allowed_hosts)):
            raise ValueError(f'重定向目标不安全: {loc}')
        resp = requests.get(loc, timeout=timeout, allow_redirects=False)
        url = loc
        seen += 1
    return resp
