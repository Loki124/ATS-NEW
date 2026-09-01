"""T6 签名 / 验签 / 重放 单元测试（离线，不触发网络）。

覆盖：
- sign/verify 往返一致
- 篡改签名 / 篡改业务字段 → 验签失败
- null / 空字符串字段不参与签名
- 重放窗口边界（4:59 通过，5:01 拒绝，5:00 边界包含）
"""
import hashlib
import hmac
import time

from apps.integration.suppliers.base import (
    BaseBackgroundCheckSupplier,
    verify_callback_signature,
    replay_allowed,
)
from apps.integration.suppliers.hmac_adapter import HmacBackgroundCheckSupplier


def _raw_sign(number, status, ts, app_key):
    sign_str = "number=" + str(number) + "&status=" + str(status) + "&timestamp=" + str(ts)
    return hmac.new(app_key.encode('utf-8'), sign_str.encode('utf-8'), hashlib.sha256).hexdigest()


def test_sign_roundtrip():
    ts = int(time.time() * 1000)
    payload = {'number': 'N1', 'status': 3, 'timestamp': ts, 'sign': _raw_sign('N1', 3, ts, 'testkey')}
    assert verify_callback_signature(payload, 'testkey') is True


def test_tampered_sign_fails():
    ts = int(time.time() * 1000)
    payload = {'number': 'N1', 'status': 3, 'timestamp': ts, 'sign': 'deadbeef'}
    assert verify_callback_signature(payload, 'testkey') is False


def test_tampered_business_field_fails():
    ts = int(time.time() * 1000)
    valid_sign = _raw_sign('N1', 3, ts, 'testkey')
    # number 在签名后变更 → 签名不匹配
    payload = {'number': 'N1-CHANGED', 'status': 3, 'timestamp': ts, 'sign': valid_sign}
    assert verify_callback_signature(payload, 'testkey') is False


def test_null_empty_fields_excluded_from_sign():
    # sign_request 必须丢弃 None / '' 之后再签名，故两种入参签名应一致
    supplier = HmacBackgroundCheckSupplier.__new__(HmacBackgroundCheckSupplier)
    supplier._app_id = 'app'
    supplier._app_key = 'k'
    h_full = supplier.sign_request({'a': '1', 'b': '', 'c': None, 'd': '2'})
    h_min = supplier.sign_request({'a': '1', 'd': '2'})
    assert h_full['X-App-Sign'] == h_min['X-App-Sign']
    assert 'X-Timestamp' in h_full and 'X-App-Sign' in h_full
    assert h_full['Content-Type'] == 'application/json'


def test_replay_window_boundary():
    now = int(time.time() * 1000)
    # 4:59 在窗口内
    assert replay_allowed(now - (4 * 60 * 1000 + 59 * 1000)) is True
    # 5:01 超出窗口
    assert replay_allowed(now - (5 * 60 * 1000 + 1000)) is False
    # 5:00 边界（≤ window）包含
    assert replay_allowed(now - 5 * 60 * 1000) is True
    assert replay_allowed(now) is True
