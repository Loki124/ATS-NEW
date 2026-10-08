"""P1-4 回归: integration/crypto.py 解密失败从 fail-open (静默返回空串) 改为 fail-closed (抛 DecryptionError)。

动机 (2026-10-08 代码审查报告 P1-4): 原 decrypt_secret 在 InvalidToken 时 `return ''`,
导致"密钥配错/轮换期旧密文"场景无任何告警地静默失败, 集成拿到空凭据却仍 200——属于
隐藏的高危失败模式。修复后必须显式抛 DecryptionError, 由 services.py / suppliers/base.py
调用方捕获并转为清晰错误 + 审计日志。

本测试锁定该 fail-closed 契约, 防止日后被人"顺手"改回静默返回空串。
"""
import pytest
from cryptography.fernet import Fernet
from django.test import override_settings

from apps.common.encryption import DecryptionError
from apps.integration.crypto import (
    decrypt_secret,
    decrypt_secret_dict,
    encrypt_secret,
)

# 隔离测试密钥, 不依赖 settings 是否配置了真实 INTEGRATION_FERNET_KEY
_TEST_KEY = Fernet.generate_key().decode()


@override_settings(INTEGRATION_FERNET_KEY=_TEST_KEY)
def test_decrypt_secret_empty_returns_empty():
    """空密文 = "未配置密钥", 仍返回 '' (fail-closed 只针对"有密文但解不开")。"""
    assert decrypt_secret('') == ''


@override_settings(INTEGRATION_FERNET_KEY=_TEST_KEY)
def test_decrypt_secret_wrong_key_raises_fail_closed():
    """密钥配错 / 轮换期旧密文 → 必须抛 DecryptionError, 不再静默返回空串。"""
    other = Fernet.generate_key().decode()
    wrong_ct = Fernet(other.encode()).encrypt(b'secret-value').decode()
    with pytest.raises(DecryptionError):
        decrypt_secret(wrong_ct)


@override_settings(INTEGRATION_FERNET_KEY=_TEST_KEY)
def test_decrypt_secret_roundtrip():
    ct = encrypt_secret('my-secret')
    assert decrypt_secret(ct) == 'my-secret'


@override_settings(INTEGRATION_FERNET_KEY=_TEST_KEY)
def test_decrypt_secret_dict_preserves_failed_key():
    """单 key 解密失败 (fail-closed) 时保留原密文, 不静默置空, 不中断其余 key 解密。"""
    good_ct = encrypt_secret('v')
    d = {'good': good_ct, 'bad': 'not-a-valid-token'}
    out = decrypt_secret_dict(d, ['good', 'bad'])
    assert out['good'] == 'v'
    # 失败 key 保留密文原值, 让调用方用"仍是密文"识别失败, 而非误判为"无密钥"
    assert out['bad'] == 'not-a-valid-token'
