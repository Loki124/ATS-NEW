"""通用工具函数"""
import re
from typing import Any, Dict, List, Optional


def normalize_phone(phone: str) -> str:
    """规范化手机号（去空格、加86前缀）"""
    if not phone:
        return phone
    phone = re.sub(r'\D', '', phone)
    if phone.startswith('86') and len(phone) == 13:
        return phone
    if len(phone) == 11:
        return f'86{phone}'
    return phone


def mask_sensitive(value: str, mask_char: str = '*', keep_prefix: int = 0, keep_suffix: int = 0) -> str:
    """脱敏"""
    if not value:
        return value
    if len(value) <= keep_prefix + keep_suffix:
        return mask_char * len(value)
    middle = len(value) - keep_prefix - keep_suffix
    return value[:keep_prefix] + mask_char * middle + value[-keep_suffix:] if keep_suffix else value[:keep_prefix] + mask_char * middle


def mask_phone(phone: str) -> str:
    """手机号脱敏 138****1234"""
    if not phone or len(phone) < 7:
        return phone
    return phone[:3] + '****' + phone[-4:]


def mask_email(email: str) -> str:
    """邮箱脱敏 a***@example.com"""
    if not email or '@' not in email:
        return email
    local, domain = email.split('@', 1)
    if len(local) <= 1:
        masked = local + '***'
    else:
        masked = local[0] + '***' + local[-1] if len(local) > 2 else local + '***'
    return f'{masked}@{domain}'


def mask_id_card(id_card: str) -> str:
    """身份证号脱敏 110101********1234"""
    if not id_card or len(id_card) < 8:
        return id_card
    return id_card[:6] + '********' + id_card[-4:]


def diff_dicts(old: Dict[str, Any], new: Dict[str, Any], ignore_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """计算两个字典的差异（用于审计）"""
    ignore_keys = ignore_keys or []
    diff = {'changed': {}, 'added': {}, 'removed': {}}
    all_keys = set(old.keys()) | set(new.keys())

    for key in all_keys:
        if key in ignore_keys:
            continue
        if key in old and key in new:
            if old[key] != new[key]:
                diff['changed'][key] = {'old': old[key], 'new': new[key]}
        elif key in new:
            diff['added'][key] = new[key]
        else:
            diff['removed'][key] = old[key]

    return diff
