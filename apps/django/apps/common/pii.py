"""PII 脱敏原语 (2026-10-21 · 整改卡 C3)

放在 `apps/common/` 而不是 `apps/gdpr/` 的原因: **两处都要用**——
  - `apps.gdpr.purge` —— 被遗忘权执行时清理关联表里的 PII 副本;
  - `apps.candidate.audit` —— 审计写入端从源头不再落 PII 原值。

若把实现塞进 gdpr, candidate 审计就得反向依赖 gdpr (gdpr 已依赖 candidate),
会形成循环依赖。本模块**不依赖任何 app 的模型**, 纯文本/JSON 处理, 可安全被三方引用。

设计原则:
  1. **脱敏而非删除** —— 自由文本里的手机号/邮箱/身份证改为掩码, 上下文与业务事实保留
     (决策 3: 「面评/推荐理由/备注类文本 → 保留业务事实, 但正则脱敏其中的手机号/邮箱」);
  2. **只认白名单, 不猜语义** —— 哪些字段算 PII 由显式白名单决定 (field_key / field_type),
     不用「字段名里含 phone 就当 PII」这类模糊匹配, 避免误清业务事实;
  3. **非字符串原样返回** —— JSON 里的数字/布尔/None 不受影响。
"""
from __future__ import annotations

import re
from typing import Any

from .masking import mask_email, mask_id_card, mask_phone

# ══════════════════════════════════════════════════════════════════
# 1. 自由文本脱敏
# ══════════════════════════════════════════════════════════════════

# 中国大陆手机号: 支持 +86 前缀、空格/横线分隔。
# 负向前后顾断言, 避免从更长的数字串里截出 11 位误伤。
_PHONE_RE = re.compile(
    r'(?<![\d])(?:\+?86[-\s]?)?1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}(?![\d])'
)
# 邮箱: 保守匹配, 避免把普通文本里的 @ 误判
_EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
# 身份证: 18 位 (末位可 X) 或 15 位旧证
_IDCARD_RE = re.compile(
    r'(?<![0-9A-Za-z])\d{17}[\dXx](?![0-9A-Za-z])'
    r'|(?<![0-9A-Za-z])\d{15}(?![0-9A-Za-z])'
)


def _mask_phone_in_text(raw: str) -> str:
    """把一段含分隔符的号码归一后掩码 (138 1234 5678 → 138****5678)。"""
    digits = re.sub(r'\D', '', raw)
    if len(digits) >= 11:
        return f'{digits[-11:-8]}****{digits[-4:]}'
    return '*' * len(raw)


def scrub_text(value: Any) -> Any:
    """自由文本脱敏: 手机号 / 邮箱 / 身份证号 → 掩码, 其余原样保留。

    身份证**先于**手机号处理: 18 位证件号里可能含一段 "1x{9 位数字",
    若先跑手机号正则会把它从中间截成 11 位掩码, 破坏证件号结构。
    """
    if not value or not isinstance(value, str):
        return value
    out = _IDCARD_RE.sub(lambda m: mask_id_card(m.group(0)), value)
    out = _PHONE_RE.sub(lambda m: _mask_phone_in_text(m.group(0)), out)
    out = _EMAIL_RE.sub(lambda m: mask_email(m.group(0)), out)
    return out


def scrub_json(value: Any) -> Any:
    """递归脱敏 JSON 结构里的所有字符串值 (键名与结构不变)。"""
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, list):
        return [scrub_json(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub_json(v) for k, v in value.items()}
    return value


# ══════════════════════════════════════════════════════════════════
# 2. 字段白名单
# ══════════════════════════════════════════════════════════════════

#: 候选人动态字段 / 标准简历扩展字段的敏感 key 白名单。
#:
#: 口径 (兵哥 2026-10-21 拍板): **只清「身份证 / 手机 / 邮箱 / 住址」四类个人敏感项,
#: 其余保留**。额外把「姓名」纳入 —— 主表 `name` 已被 C2 匿名化, 动态字段若留着
#: name 副本, 等于"主表清了、边角没清", 被遗忘权名存实亡。
#:
#: 刻意**不**纳入的 (属招聘业务事实, 与主表 C2 口径保持一致):
#: `gender` / `ethnicity` / `birth_date*` / `current_city` / `expected_city` /
#: `work_location` / `current_company` / `current_title` / `highest_degree` 等。
SENSITIVE_FIELD_KEYS: frozenset[str] = frozenset({
    # ── 姓名 (与主表 C2 口径对齐, 姓名不清则主表匿名化被抵消) ──
    'name', 'fullname', 'full_name', 'realname', 'real_name', 'candidate_name',
    # ── 手机 / 联系方式 ──
    'mobile', 'phone', 'phone_number', 'phonenumber', 'tel', 'telephone',
    'contact', 'contact_phone', 'contactphone', 'wechat', 'weixin', 'qq',
    # ── 邮箱 ──
    'email', 'mail', 'email_address', 'emailaddress',
    # ── 身份证 ──
    'id_card_number', 'idcardnumber', 'id_card_no', 'idcardno', 'id_card',
    'idcard', 'id_no', 'idnumber', 'id_number',
    'id_card_photo_front', 'id_card_photo_back',
    'id_card_issuing_authority', 'id_card_validity_period',
    # ── 住址 ──
    'residence_address', 'home_address', 'address', 'location',
    'registered_birthplace',
})

#: 动态字段的 field_type 权威白名单 (对应 `apps.dynamic_field.models.DynamicField.FieldType`)。
#: `dynamic_field_values` 的 field_key 与 `DynamicField.field_key` 对齐 → 可直接 join 取类型,
#: 比按 key 猜更可靠。类型值用裸字符串而非 import 模型, 避免 common → app 的反向依赖。
PII_FIELD_TYPES: frozenset[str] = frozenset({
    'ID_CARD', 'BANK_CARD', 'PHONE', 'EMAIL', 'ADDRESS',
})

#: 审计 `changes[].old/new` 里需要整体隐去 (而非掩码) 的字段 ——
#: 姓名与简历正文无法用掩码表达 (掩码后仍能看出长度/首字), 直接置占位符。
REDACT_ENTIRELY_FIELDS: frozenset[str] = frozenset({
    'name', 'full_name', 'resume_text', 'resume_file_url',
})

#: 整体隐去时写入的占位符
REDACTED_PLACEHOLDER = '（已按被遗忘权隐去）'


def is_sensitive_field_key(key: str | None) -> bool:
    """字段 key 是否在敏感白名单内 (大小写不敏感)。"""
    if not key:
        return False
    return str(key).strip().lower() in SENSITIVE_FIELD_KEYS


def redact_field_value(field: str | None, value: Any) -> Any:
    """按**字段名**脱敏单个值 —— 审计写入端与清理端共用。

    - 姓名 / 简历正文 / 简历文件 URL → 整体隐去 (掩码无意义)
    - 手机 / 邮箱 / 身份证 → 掩码 (保留"有值 vs 空值"的信息)
    - 其它字段 → 退化为自由文本脱敏 (可能夹带联系方式)
    """
    if value is None or value == '':
        return value
    name = str(field or '').strip().lower()
    if name in REDACT_ENTIRELY_FIELDS:
        return REDACTED_PLACEHOLDER
    if not isinstance(value, str):
        return value
    if name in ('phone', 'mobile', 'contact_phone'):
        return mask_phone(value)
    if name in ('email', 'mail'):
        return mask_email(value)
    if name in ('id_card_no', 'id_card_number', 'idcard', 'idcardno', 'id_no'):
        return mask_id_card(value)
    return scrub_text(value)
