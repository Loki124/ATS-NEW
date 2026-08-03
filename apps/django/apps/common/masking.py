"""PII 脱敏工具 (2026-08-03 R2 / R15 寇豆码)

项目里原本有三处各写各的脱敏逻辑:
  - apps/field_acl/services.py:FieldAclService._mask_value  (有实现, 但零业务调用)
  - apps/application/serializers.py:92 get_candidate_phone  (全项目唯一真实生效的)
  - 其它地方直接吐明文

这里抽成单一实现, 供 field_acl / serializer / model.__str__ 共用,
避免同一个手机号在列表页是 138****8000、在日志里是明文。

约定: 所有函数对空值 (None / '') 原样返回, 不抛异常, 不吞掉类型信息。
"""
from __future__ import annotations

from typing import Any, Optional

#: 掩码占位符
MASK_TOKEN = '***'


def mask_phone(value: Optional[str]) -> str:
    """手机号: 13812348000 -> 138****8000; 短号码整体打码."""
    if not value:
        return '' if value is None else value
    s = str(value)
    if len(s) >= 7:
        return f'{s[:3]}****{s[-4:]}'
    return '*' * len(s)


def mask_phone_tail(value: Optional[str]) -> str:
    """只保留后 4 位: 13812348000 -> ***8000 的更严格版本, 用于日志 / __str__.

    R15: Candidate.__str__ 会被 Django admin / repr / logger 反复调用,
    一旦进日志就等于明文 PII 落盘, 所以这里连号段都不保留。
    """
    if not value:
        return ''
    s = str(value)
    if len(s) >= 4:
        return f'{MASK_TOKEN}{s[-4:]}'
    return MASK_TOKEN


def mask_email(value: Optional[str]) -> str:
    """邮箱: alice@example.com -> a***@example.com."""
    if not value:
        return '' if value is None else value
    s = str(value)
    if '@' not in s:
        return mask_generic(s)
    local, domain = s.split('@', 1)
    if len(local) > 1:
        return f'{local[0]}***@{domain}'
    return f'***@{domain}'


def mask_id_card(value: Optional[str]) -> str:
    """身份证: 110101199001011234 -> 110***********1234."""
    if not value:
        return '' if value is None else value
    s = str(value)
    if len(s) >= 8:
        return f'{s[:3]}{"*" * (len(s) - 7)}{s[-4:]}'
    return '*' * len(s)


def mask_amount(value: Any) -> str:
    """薪资等金额: 一律 '***' (区间也能被反推, 不做部分保留)."""
    if value is None or value == '':
        return value
    return MASK_TOKEN


def mask_generic(value: Any) -> str:
    """通用: 首尾各留 1 位, 中间打码; 长度 <= 4 全打码."""
    if value is None or value == '':
        return value
    s = str(value)
    if len(s) > 4:
        return f'{s[0]}{"*" * (len(s) - 2)}{s[-1]}'
    return '*' * len(s)
