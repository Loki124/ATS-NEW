"""背调测试共享工具：回调签名 / 构造回调体。"""
import hashlib
import hmac
import time


def sign_callback(number, status, ts, app_key):
    """§5.2 回调签名：与 suppliers.base.verify_callback_signature 同公式（供测试构造合法 payload）。"""
    sign_str = "number=" + str(number) + "&status=" + str(status) + "&timestamp=" + str(ts)
    return hmac.new(
        app_key.encode('utf-8'), sign_str.encode('utf-8'), hashlib.sha256,
    ).hexdigest()


def make_payload(number, status, app_key='testkey', ts=None, **extra):
    """构造带合法签名的回调 payload；extra 可附加 statusName/riskLevel/reportUrl/completionTime。"""
    ts = ts if ts is not None else int(time.time() * 1000)
    payload = {
        'number': number,
        'status': status,
        'timestamp': ts,
        'sign': sign_callback(number, status, ts, app_key),
    }
    payload.update(extra)
    return payload
