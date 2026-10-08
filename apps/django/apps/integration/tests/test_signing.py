"""T6 签名 / 验签 / 重放 单元测试（离线，不触发网络）。

覆盖：
- sign/verify 往返一致
- 篡改签名 / 篡改业务字段 → 验签失败
- null / 空字符串字段不参与签名
- 重放窗口边界（4:59 通过，5:01 拒绝，5:00 边界包含）
- 出向签名实际 HMAC 值锁定（含 list 复合值，验证 §1.4.3 JSON 编码）
"""
import hashlib
import hmac
import json
import time
from unittest.mock import patch

from apps.integration.suppliers.base import (
    BaseBackgroundCheckSupplier,
    replay_allowed,
    verify_callback_signature,
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


def _expected_sign(params: dict, app_key: str, ts: int) -> str:
    """独立 oracle：按 §1.4.3（含复合值 JSON 紧凑编码）重算 HMAC，不依赖实现。"""
    biz = {k: v for k, v in params.items() if v is not None and v != ''}
    def _enc(v):
        if isinstance(v, str):
            return v
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if isinstance(v, (int, float)):
            return json.dumps(v)
        return json.dumps(v, separators=(',', ':'), ensure_ascii=False)
    raw = '&'.join(f'{k}={_enc(v)}' for k, v in sorted(biz.items()))
    sign_str = f'{raw}&timestamp={ts}' if raw else f'timestamp={ts}'
    return hmac.new(app_key.encode('utf-8'), sign_str.encode('utf-8'), hashlib.sha256).hexdigest()


def test_sign_request_hmac_value_with_list_field():
    """锁定出向签名实际 HMAC 值：含 list 复合值，验证编码为 JSON 而非 repr。"""
    supplier = HmacBackgroundCheckSupplier.__new__(HmacBackgroundCheckSupplier)
    supplier._app_id = 'sp_test'
    supplier._app_key = 'testkey'
    ts = 1700000000000
    params = {'requestId': 'R1', 'candidateId': 'C1', 'items': ['edu', 'work']}
    with patch('time.time', return_value=1700000000.0):
        headers = supplier.sign_request(params)
    assert headers['X-Timestamp'] == str(ts)
    assert headers['X-App-Sign'] == _expected_sign(params, 'testkey', ts)
    # 关键不变量：list 值按 JSON 编码，绝不能出现 repr 的 ``['edu', 'work']`` 形态
    assert "['edu', 'work']" not in headers['X-App-Sign']
    # oracle 显式使用 JSON 紧凑串，证明实现与之逐字节一致
    oracle_str = 'candidateId=C1&items=["edu","work"]&requestId=R1&timestamp=1700000000000'
    assert headers['X-App-Sign'] == hmac.new(
        b'testkey', oracle_str.encode('utf-8'), hashlib.sha256,
    ).hexdigest()


def test_sign_request_hmac_value_stable_across_int_and_bool():
    """int / bool / 字符串混排时，签名值稳定且编码符合 §1.4.3。"""
    supplier = HmacBackgroundCheckSupplier.__new__(HmacBackgroundCheckSupplier)
    supplier._app_id = 'sp_test'
    supplier._app_key = 'testkey'
    ts = 1700000000000
    params = {'authWay': 1, 'contactCandidate': True, 'name': '张三'}
    with patch('time.time', return_value=1700000000.0):
        headers = supplier.sign_request(params)
    assert headers['X-App-Sign'] == _expected_sign(params, 'testkey', ts)
