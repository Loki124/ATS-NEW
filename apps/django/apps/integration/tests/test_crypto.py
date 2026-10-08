"""P1-Fix4 回归锁: decrypt_secret 失败模式 fail-closed.

修复前: 无效/乱码 token 被静默捕获并返回 '' (fail-open) —— 密钥配错 / 轮换期旧密文时,
集成因"静默空串"失败却无任何告警, 极难排查.

修复后 (crypto.py):
- 空密文 ('') 仍返回 '' (视为"未配置密钥", 与调用方无密钥分支一致);
- InvalidToken / ValueError (乱码/错密钥) 抛 apps.common.encryption.DecryptionError,
  由 services.py / suppliers/base.py 调用方捕获转为清晰错误.

本文件锁定上述两条语义, 防止 fail-open 回归.
"""
import pytest
from cryptography.fernet import Fernet
from django.test import override_settings

from apps.common.encryption import DecryptionError
from apps.integration.crypto import (
    decrypt_secret,
    decrypt_secret_dict,
    encrypt_secret,
    _fernet,
)

# 测试内自生成密钥, 避免依赖环境 INTEGRATION_FERNET_KEY.
_KEY_A = Fernet.generate_key().decode()
_KEY_B = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def _use_test_key():
    """临时把 INTEGRATION_FERNET_KEY 设为测试密钥, 并清掉 _fernet 的 lru_cache."""
    with override_settings(INTEGRATION_FERNET_KEY=_KEY_A):
        _fernet.cache_clear()
        yield
        _fernet.cache_clear()


def test_empty_ciphertext_returns_empty_string():
    """Fix4: 空密文仍返回 '', 不抛异常 (fail-closed 只针对"有密文但解不开")."""
    assert decrypt_secret('') == ''


def test_roundtrip_ok():
    """基线: 合法令牌可正常加解密, 证明测试密钥已正确装配."""
    ct = encrypt_secret('super-secret')
    assert decrypt_secret(ct) == 'super-secret'


def test_garbled_token_raises_decryption_error():
    """Fix4(核心): 乱码/非法 Fernet token 必须抛 DecryptionError, 而非静默返回 ''."""
    with pytest.raises(DecryptionError):
        decrypt_secret('!!!not-a-valid-fernet-token!!!')


def test_wrong_key_raises_decryption_error():
    """Fix4(核心): 密钥配错 / 轮换期旧密文 (用 KEY_B 加密, 当前 KEY_A 解密) → DecryptionError."""
    ct = Fernet(_KEY_B.encode()).encrypt(b'payload').decode()
    with pytest.raises(DecryptionError):
        decrypt_secret(ct)


def test_decrypt_secret_dict_preserves_failed_value():
    """Fix4: decrypt_secret_dict 单 key 失败记日志并保留原密文(不被置 ''),
    让调用方用"仍是密文"识别失败, 不误导为"无密钥"."""
    good = encrypt_secret('ok-value')
    out = decrypt_secret_dict(
        {'a': good, 'b': '!!!garbage-token!!!'}, ['a', 'b'])
    assert out['a'] == 'ok-value'
    # b 解密失败 → 保留原密文
    assert out['b'] == '!!!garbage-token!!!'
