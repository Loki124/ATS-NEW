"""加密工具 - 集成密钥/敏感配置加解密 (Fix 6)

使用 Fernet (AES-128-CBC + HMAC-SHA256).
密钥从 settings.INTEGRATION_FERNET_KEY 读取, 应通过 env 注入.

老 config JSON 字段保留作为非敏感配置 (URL / 签名名 等),
新 secret 字段 (encrypted_secret) 存敏感凭据 (access_key_secret, corp_secret, smtp_password 等).
"""
from __future__ import annotations

import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from apps.common.encryption import DecryptionError

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
    """解密敏感字符串.

    失败模式 (P1 修复, 原 fail-open 静默返回空串 → fail-closed 明确异常):
    InvalidToken / 解析失败抛 DecryptionError, 由 services.py / suppliers/base.py 调用方
    捕获并转为清晰错误, 避免集成因「静默空串」而失败却无告警 (密钥配错 / 轮换期旧密文).

    空密文(ciphertext 为空)视为"未配置密钥", 直接返回 '' —— 与调用方"无密钥"分支一致,
    不抛异常 (fail-closed 只针对"有密文但解不开"的明确失败).
    """
    if not ciphertext:
        return ''
    try:
        return _fernet().decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError) as e:
        raise DecryptionError(
            f'IntegrationConfig 密钥解密失败 (fail-closed): err_type={type(e).__name__}'
        ) from e


def encrypt_secret_dict(d: dict, keys: list) -> dict:
    """加密 dict 中指定 keys 的 value, 返回新 dict."""
    out = dict(d)
    for k in keys:
        if k in out and out[k]:
            out[k] = encrypt_secret(str(out[k]))
    return out


def decrypt_secret_dict(d: dict, keys: list) -> dict:
    """解密 dict 中指定 keys 的 value, 返回新 dict.

    单 key 解密失败 (fail-closed DecryptionError) 记日志并保留原值, 不中断其余 key 解密;
    保留原值(密文)而非静默置 '' 可让调用方用"仍是密文"识别失败, 不误导为"无密钥".
    """
    out = dict(d)
    for k in keys:
        if k in out and out[k]:
            try:
                out[k] = decrypt_secret(str(out[k]))
            except DecryptionError as e:
                logger.warning('decrypt_secret_dict: key=%s 解密失败: %s', k, e)
    return out


# 各集成类型的敏感字段 (业务侧引用)
SENSITIVE_KEYS: dict[str, list[str]] = {
    'EMAIL': ['password', 'smtp_password'],
    'WECOM': ['corp_secret'],
    'MOKA': ['api_key', 'api_secret'],
    'SMS': ['access_key_secret'],
    'BACKGROUND_CHECK': ['api_key'],
}