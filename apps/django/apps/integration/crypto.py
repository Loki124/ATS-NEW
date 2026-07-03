"""加密工具 - 集成密钥/敏感配置加解密 (Fix 6)

使用 Fernet (AES-128-CBC + HMAC-SHA256).
密钥从 settings.INTEGRATION_FERNET_KEY 读取, 应通过 env 注入.

老 config JSON 字段保留作为非敏感配置 (URL / 签名名 等),
新 secret 字段 (encrypted_secret) 存敏感凭据 (access_key_secret, corp_secret, smtp_password 等).
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from django.conf import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """获取 Fernet 实例. 若 key 未配置则抛 ImproperlyConfigured."""
    key = getattr(settings, 'INTEGRATION_FERNET_KEY', None)
    if not key:
        raise RuntimeError(
            'INTEGRATION_FERNET_KEY 未配置. '
            '请在 .env 中设置 32-byte base64 密钥: '
            '`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(plaintext: str) -> str:
    """加密敏感字符串, 返回 base64 字符串."""
    return _fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def decrypt_secret(ciphertext: str) -> str:
    """解密敏感字符串. 无效 token 返回空串并 log 警告."""
    try:
        return _fernet().decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError) as e:
        logger.warning('decrypt_secret: invalid token: %s', e)
        return ''


def encrypt_secret_dict(d: dict, keys: list) -> dict:
    """加密 dict 中指定 keys 的 value, 返回新 dict."""
    out = dict(d)
    for k in keys:
        if k in out and out[k]:
            out[k] = encrypt_secret(str(out[k]))
    return out


def decrypt_secret_dict(d: dict, keys: list) -> dict:
    """解密 dict 中指定 keys 的 value, 返回新 dict."""
    out = dict(d)
    for k in keys:
        if k in out and out[k]:
            out[k] = decrypt_secret(str(out[k]))
    return out


# 各集成类型的敏感字段 (业务侧引用)
SENSITIVE_KEYS: dict[str, list[str]] = {
    'EMAIL': ['password', 'smtp_password'],
    'WECOM': ['corp_secret'],
    'MOKA': ['api_key', 'api_secret'],
    'SMS': ['access_key_secret'],
    'BACKGROUND_CHECK': ['api_key'],
}