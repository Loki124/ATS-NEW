"""字段级加密 (2026-08-03 S3)

PII (Personally Identifiable Information) 字段级加密方案:
- Fernet (cryptography 库) 对称加密, AES-128-CBC + HMAC-SHA256
- Key 走环境变量 ENCRYPTION_KEY, 生产必须设
- 字段类型 EncryptedCharField, 自动加解密, 应用层 API 不变
- 索引限制: 加密字段不能直接 filter/search, 用 hash 字段 (PHONE_HASH/EMAIL_HASH) 做查重

文件命名: `encryption.py` (不在 models.py 避免循环 import)

为什么不用 django-cryptography / django-fernet-fields:
- 维护不活跃 (最后版本 1.1 / 0.6 都是 2022)
- 引入额外依赖
- 我们的需求简单 (CharField 加密), 50 行代码自己实现
- 跟 INTEGRATION_FERNET_KEY 复用同一个 key
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """获取 Fernet 实例. 优先用 ENCRYPTION_KEY, fallback 到 INTEGRATION_FERNET_KEY.

    复用 INTEGRATION_FERNET_KEY 是因为:
    1) 都是 Fernet 加密, 同一 key 可用
    2) 减少环境变量, 降低运维复杂度
    3) 如果未来 key rotation, 两个用途一起切换

    生产必须显式设 ENCRYPTION_KEY 或 INTEGRATION_FERNET_KEY, 否则启动报错.
    """
    key = (
        getattr(settings, 'ENCRYPTION_KEY', None)
        or getattr(settings, 'INTEGRATION_FERNET_KEY', None)
        or ''
    )
    if not key:
        raise ImproperlyConfigured(
            'PII 字段加密需要 ENCRYPTION_KEY (或 INTEGRATION_FERNET_KEY) 环境变量. '
            '生成方法: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        raise ImproperlyConfigured(
            f'ENCRYPTION_KEY 格式错误 (不是有效 Fernet key): {e}'
        ) from e


def encrypt_value(plaintext: Optional[str]) -> Optional[str]:
    """加密字符串. None/空 返 None (不加密, 节省存储)."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def decrypt_value(ciphertext: Optional[str]) -> Optional[str]:
    """解密字符串. None/空 返 None. 解密失败返原值 + WARNING log (兼容老数据 / 错误数据)."""
    if not ciphertext:
        return ciphertext
    # 快速判断: Fernet token 是 base64 编码, 长度 ~ 200
    # 如果不是 Fernet 格式 (例如老数据明文), 尝试当明文返
    try:
        return _get_fernet().decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError, TypeError):
        # 不是加密格式 — 可能是迁移前明文, 直接返
        logger.warning('PII decrypt failed: 数据可能未加密 (明文 fallback). ciphertext prefix=%r', ciphertext[:30])
        return ciphertext


def hash_for_search(plaintext: Optional[str], salt: str = 'ats-pii') -> str:
    """用于搜索/查重的不可逆 hash.

    用 HMAC-SHA256 而不是裸 SHA256 (加项目级 salt 防彩虹表).
    同明文 → 同 hash, 支持 .filter(hash_field=...).

    注意: 不用于认证 (那是 GDPR verification code 的活), 只用于查重.
    """
    if not plaintext:
        return ''
    h = hashlib.sha256()
    h.update(salt.encode('utf-8'))
    h.update(b':')
    h.update(plaintext.strip().lower().encode('utf-8'))  # 标准化
    return h.hexdigest()


class EncryptedCharField(models.CharField):
    """字段级加密 CharField.

    用法:
        class Candidate(models.Model):
            id_card_no = EncryptedCharField(max_length=512, blank=True)

    行为:
        - Python 层: 透明, 读写都是明文
        - DB 层: 存密文 (Fernet 加密, ~200 字符/字段, 所以 max_length=512)
        - 不能直接 filter(field='value'), 必须用 hash 字段 (见 hash_for_search)
        - 不参与 index (unique_together)
    """

    description = 'Fernet 加密的 CharField'

    def from_db_value(self, value, expression, connection):
        """DB 读出来时自动解密"""
        if value is None:
            return value
        return decrypt_value(value)

    def to_python(self, value):
        """反序列化时解密 (例如 from serializers)"""
        if isinstance(value, str) or value is None:
            return decrypt_value(value) if value else value
        return value

    def get_prep_value(self, value):
        """写入 DB 前加密"""
        if value is None or value == '':
            return value
        return encrypt_value(value)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # 不在 migration 写出加密细节, 保持 max_length 等字段属性
        return name, path, args, kwargs
