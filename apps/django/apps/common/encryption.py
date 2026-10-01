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

import binascii
import hashlib
import logging
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger(__name__)


class DecryptionError(Exception):
    """解密失败且 STRICT_DECRYPT=True 时抛出 (fail-closed).

    为什么需要它: 历史实现在 Fernet 解密失败时**返回密文原值** (fail-open), 一旦
    生产密钥配错、或密钥轮换期新旧数据未同步, 所有 PII 加密字段会静默以密文形态
    返回业务层 —— 表单乱码、查重失效、第三方集成拿到错误凭据, 而系统无任何显式
    报错来触发告警。对以「候选人隐私保护」为卖点的 ATS, 加密层失败模式必须是
    fail-closed: 宁可请求失败并告警, 也不静默返回不可信数据。

    来源: 2026-09-27 全面技术分析报告 P0-1。
    """


def _single_key() -> str:
    """取单密钥: 优先 ENCRYPTION_KEY, fallback 到 INTEGRATION_FERNET_KEY.

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
    return key


def _mk_fernet(key) -> Fernet:
    """由单个 key 构造 Fernet, 格式错误时抛 ImproperlyConfigured."""
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError, binascii.Error) as e:  # Fernet 构造异常类型不固定 (ValueError/binascii.Error 等), 统一 ImproperlyConfigured
        raise ImproperlyConfigured(
            f'ENCRYPTION_KEY 格式错误 (不是有效 Fernet key): {e}'
        ) from e


def _get_fernet():
    """获取 Fernet / MultiFernet 实例.

    2026-09-27 P2-2: 支持密钥轮换. ENCRYPTION_KEYS 为逗号分隔的多个 key 时返回
    MultiFernet —— 第一个为主密钥(用于加密), 全部 key 依次尝试解密,
    于是"新密钥加密 + 前密钥仍可读"的平滑轮换成为可能。未配置则退化为单密钥。
    """
    keys_raw = getattr(settings, 'ENCRYPTION_KEYS', '') or ''
    keys = [k.strip() for k in keys_raw.split(',') if k.strip()]
    if len(keys) > 1:
        return MultiFernet([_mk_fernet(k) for k in keys])
    if len(keys) == 1:
        return _mk_fernet(keys[0])
    return _mk_fernet(_single_key())


def encrypt_value(plaintext: Optional[str]) -> Optional[str]:
    """加密字符串. None/空 返 None (不加密, 节省存储)."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def decrypt_value(ciphertext: Optional[str], field_name: Optional[str] = None) -> Optional[str]:
    """解密字符串. None/空 返 None.

    失败模式 (2026-09-27 P0-1 修复, 原 fail-open 静默返回密文):
    - STRICT_DECRYPT=True  (生产默认): 抛 DecryptionError —— fail-closed, 由全局
      异常处理上报, 绝不把不可信数据交给业务层。
    - STRICT_DECRYPT=False (base/迁移过渡期): 记 warning 后返回原值 (历史行为),
      仅作为密钥轮换过渡期的临时降级, 过渡结束必须移除。

    日志安全: 绝不把密文/明文内容写进日志 (原实现会写 ciphertext[:30])。
    只记字段名 + 错误类型 + 是否疑似 Fernet token, 便于定位又不泄露数据。
    """
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError, TypeError) as e:
        # Fernet token 恒以 'gAAAAA' 开头, 用它区分"密文解不开"和"历史明文"
        looks_encrypted = str(ciphertext).startswith('gAAAAA')
        where = field_name or '<unknown>'
        if getattr(settings, 'STRICT_DECRYPT', False):
            raise DecryptionError(
                'PII 解密失败 (STRICT_DECRYPT=True, fail-closed): '
                f'field={where} err_type={type(e).__name__} '
                f'looks_encrypted={looks_encrypted}'
            ) from e
        logger.warning(
            'PII decrypt failed: 明文 fallback (fail-open, 建议排查密钥配置). '
            'field=%s err_type=%s looks_encrypted=%s',
            where, type(e).__name__, looks_encrypted,
        )
        return ciphertext


# 2026-09-27 P0-2: 历史 salt 写死在源码里, 而本仓库是公开仓库 —— 拿到源码即拿到 salt,
# 手机号(11 位数字, 空间仅 ~10^10)可被离线预计算彩虹表反查. salt 必须来自环境变量.
# LEGACY_HASH_SALT 仅为兼容存量数据保留, 新部署必须设 PII_HASH_SALT.
LEGACY_HASH_SALT = 'ats-pii'
# 版本前缀: 存量 v1 无前缀; 启用外部 salt 后产出 v2_ 前缀, 便于双读与灰度切换.
HASH_V2_PREFIX = 'v2_'

# ⚠️ 哈希列当前 max_length=64 (migration 0006), 而 v2_ 前缀 + 64 位 hex = 67 字符.
#    启用 PII_HASH_SALT 前必须先扩列到 >= 80, 否则写入会被截断/报错.
HASH_V2_REQUIRED_MAX_LENGTH = 80


def _digest(salt: str, plaintext: str) -> str:
    """salt 前置的 SHA-256 (标准化: strip + lower). 同明文 → 同 digest."""
    h = hashlib.sha256()
    h.update(salt.encode('utf-8'))
    h.update(b':')
    h.update(plaintext.strip().lower().encode('utf-8'))
    return h.hexdigest()


def hash_for_search(plaintext: Optional[str], salt: Optional[str] = None) -> str:
    """用于搜索/查重的不可逆 hash (salt 前置的 SHA-256).

    算法说明: 实现是 **salt 前置的 SHA-256** (salt + ':' + 标准化明文), 不是 HMAC
    —— 原 docstring 写"HMAC-SHA256"属描述错误, 已更正; 构造本身不变以保证存量哈希
    仍然可比对, 真正的安全缺陷是 salt 写死在源码 (见 LEGACY_HASH_SALT 注释)。

    salt 解析优先级:
    1) 显式传 salt  → 用传入值, 产出无前缀 digest (兼容老调用方/迁移回填)
    2) 设了 PII_HASH_SALT → 用外部 salt, 产出带 'v2_' 前缀的 digest
    3) 都没设        → 沿用 LEGACY_HASH_SALT, 产出无前缀 digest (零行为变更)

    注意: 不用于认证 (那是 GDPR verification code 的活), 只用于查重.
    """
    if not plaintext:
        return ''
    if salt is not None:
        return _digest(salt, plaintext)
    configured = (getattr(settings, 'PII_HASH_SALT', '') or '').strip()
    if configured:
        return HASH_V2_PREFIX + _digest(configured, plaintext)
    # 未配置外部 salt: 与历史实现逐字节一致, 存量数据不受影响
    return _digest(LEGACY_HASH_SALT, plaintext)


def verify_hash_for_search(
    plaintext: Optional[str], stored_hash: Optional[str], salt: Optional[str] = None
) -> bool:
    """双读校验: 同时兼容 v1(存量) 与 v2(外部 salt), 供灰度切换期查重使用.

    为什么要双读: 一旦启用 PII_HASH_SALT, 新写入哈希与存量不同; 若查重只比 v2,
    在回填完成前会漏判(重复候选人进库); 只比 v1 则切换后失效。双读让"启用 salt →
    后台回填 → 切到单读"三段式平滑轮换成为可能, 无需改业务代码。
    """
    if not plaintext or not stored_hash:
        return False
    candidates = {_digest(LEGACY_HASH_SALT, plaintext)}
    if salt:
        candidates.add(_digest(salt, plaintext))
    configured = (getattr(settings, 'PII_HASH_SALT', '') or '').strip()
    if configured:
        candidates.add(HASH_V2_PREFIX + _digest(configured, plaintext))
    return stored_hash in candidates


def hash_candidates_for_search(
    plaintext: Optional[str], salt: Optional[str] = None
) -> list:
    """返回该明文**所有可能已落库**的哈希形态, 供 DB 层 OR 查询做双读。

    这是 P0-2 轮换能安全落地的关键: 启用 PII_HASH_SALT 后, 新写入的是 v2_,
    存量仍是 v1。查重若只比一种形态, 回填期必然漏判 (重复候选人进库)。
    用本函数把两种形态都交给 `Q(field__in=[...])`, 新旧数据都能命中,
    "启用 salt → 后台回填 → 收敛为单读" 三段式轮换才不会中断业务。

    - 未配 PII_HASH_SALT: [v1]  (与历史完全一致)
    - 已配:               [v1, v2]
    """
    if not plaintext:
        return []
    out = [_digest(LEGACY_HASH_SALT, plaintext)]
    if salt:
        extra = _digest(salt, plaintext)
        if extra not in out:
            out.append(extra)
    configured = (getattr(settings, 'PII_HASH_SALT', '') or '').strip()
    if configured:
        v2 = HASH_V2_PREFIX + _digest(configured, plaintext)
        if v2 not in out:
            out.append(v2)
    return out


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

    ⚠️ 已知容量上限 (2026-09-27 审计报告 P2-3): Fernet 密文相对明文膨胀约 1.35 倍
    + 固定开销, 因此 max_length=512 的字段实际只能容纳约 370 字符明文, 更长文本
    会在 DB 层报错。彻底解法是把底层改为 TextField; 此处保留 CharField 以免触发
    全表迁移, 新增长文本 PII 字段请直接用 TextField 子类。
    """

    description = 'Fernet 加密的 CharField'

    def from_db_value(self, value, expression, connection):
        """DB 读出来时自动解密"""
        if value is None:
            return value
        # 带上字段名, 让 fail-closed 的 DecryptionError 能指认具体字段
        return decrypt_value(value, field_name=getattr(self, 'name', None))

    def to_python(self, value):
        """反序列化时解密 (例如 from serializers)"""
        if isinstance(value, str) or value is None:
            return decrypt_value(value, field_name=getattr(self, 'name', None)) if value else value
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
