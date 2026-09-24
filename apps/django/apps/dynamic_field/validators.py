"""动态字段「限制条件」校验内核 (G42 增强, 2026-09-24 兵哥)。

设计目标
--------
在「字段管理模块」为不同字段类型配置差异化限制条件, 并在数据录入/提交时
同时做后端校验与前端拦截。本模块是后端权威校验的唯一真源, 前端拦截复用同一套规则。

字段类型 → 限制条件映射 (与 DynamicField.FieldType 对齐):
  - 文本类 (TEXT / MULTILINE_TEXT / ADDRESS)
        → 最大字数 (maxLength)   [无内容格式配置; 仅长度约束]
  - 专用格式 (EMAIL / PHONE / ID_CARD / BANK_CARD / URL)
        → 类型层面固有格式校验 (无配置项; 电话支持国际区号, 格式与长度在类型层约束)
  - 数字类 (NUMBER)
        → 最小值 (min) / 最大值 (max) / 步长 (step) / 小数位数 (decimals) + 单位 (unit)
  - 选项类 (LIST_SINGLE / LIST_MULTI)
        → 可选范围 (allowedValues, 限定只能从这些值里选)
  - 日期类 (DATE / DATE_RANGE)
        → 日期可选范围 (minDate / maxDate, 限制可选择的日期区间)
  - 下拉类 (SELECT / MULTISELECT) / 富文本 (RICH_TEXT) / 其他
        → 无限制条件配置 (下拉类可选范围由 options 全量决定; 富文本内容自由放行)

``validation`` 字段形态 (复用并规范化, 向后兼容):
  数字类:  {"min":0,"max":12,"step":1,"decimals":0,"unit":"人","message":""}
  文本类:  {"maxLength":200,"message":""}
  选项类:  {"allowedValues":["a","b"],"message":""}
  日期类:  {"minDate":"2020-01-01","maxDate":"2030-12-31","message":""}
  message 缺省时按规则自动生成默认错误文案。

向后兼容
--------
旧预设仅使用数字类的松散 {"min":N} / {"min":N,"max":N}, 其键名与规范化后的数字类形态
完全一致 (min/max 直接出现在顶层), 因此无需迁移即可被本校验器识别。
"""
from __future__ import annotations

import datetime
import re

# ---------------------------------------------------------------------------
# 类型分组 (与 models.DynamicField 的 FieldType 对齐)
# ---------------------------------------------------------------------------

#: 文本类字段 (广义: 含 EMAIL/PHONE/ID_CARD/BANK_CARD/URL 等类型层有格式约束的)
TEXT_TYPES = frozenset({
    'TEXT', 'MULTILINE_TEXT', 'ADDRESS', 'EMAIL', 'PHONE', 'ID_CARD', 'BANK_CARD', 'URL',
})

#: 文本类字段中可配置「最大字数」的 (EMAIL/PHONE 等专用格式类型由类型层约束, 不在此列)
TEXT_MAXLENGTH_TYPES = frozenset({
    'TEXT', 'MULTILINE_TEXT', 'ADDRESS', 'ID_CARD', 'BANK_CARD', 'URL',
})

#: 类型层面有固有格式校验的 (无需配置项, 由字段类型直接约束格式与长度)
TEXT_WITH_FORMAT_TYPES = frozenset({'EMAIL', 'PHONE', 'ID_CARD', 'BANK_CARD', 'URL'})

#: 数字类字段
NUMBER_TYPES = frozenset({'NUMBER'})

#: 选项类字段 (可做 可选范围 校验) — 仅列表型 (下拉型 SELECT/MULTISELECT 无配置项)
OPTION_TYPES = frozenset({'LIST_SINGLE', 'LIST_MULTI'})

#: 日期类字段 (可做 日期可选范围 校验)
DATE_TYPES = frozenset({'DATE', 'DATE_RANGE'})

#: 内容格式枚举 → 内置正则 (CUSTOM 用 pattern 自定义)
#: 注: 自 2026-09-24 起, 文本类不再暴露「内容格式」配置项; 下列仅用于类型层固有格式校验。
TEXT_FORMAT_PATTERNS: dict[str, str | None] = {
    'NONE': None,
    'EMAIL': r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$',
    'URL': r'^https?://[^\s]+$',
    # 2026-09-24 (兵哥): 电话改国际区号格式 — 存储为 +{国家码}{号码} (无分隔), 总长 6~15 位 (E.164)
    'PHONE': r'^\+\d{6,15}$',
    'ID_CARD': r'^\d{17}[\dXx]$',
    'BANK_CARD': r'^\d{16,19}$',
    'CUSTOM': None,  # 使用 pattern
}

#: EMAIL/PHONE/ID_CARD/BANK_CARD/URL 这些专用类型自带固有格式, 即便未显式配置 format 也强制校验
INHERENT_FORMAT: dict[str, str] = {
    'EMAIL': 'EMAIL',
    'PHONE': 'PHONE',
    'ID_CARD': 'ID_CARD',
    'BANK_CARD': 'BANK_CARD',
    'URL': 'URL',
}


def _parse_date(value):
    """把 'YYYY-MM-DD' 或 'YYYY-MM-DD...' 解析为 date; 非法/空返回 None。"""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _coerce_number(value):
    """把输入规整为 float; 无法解析时返回 None。

    支持 int / float / 数字字符串 / 布尔(False→0 不期望, 但跳过)。空值/None 返回 None。
    """
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (TypeError, ValueError):
            return None
    return None


def normalize_validation(field_type: str, validation) -> dict:
    """按字段类型把一个可能松散/非法的 ``validation`` 规整为规范化 dict。

    规则:
      - 非 dict / None → 返回 {}
      - 数字类: 提取 min/max/step/decimals (强制转 float/int, 非法则丢弃), 保留 message
      - 文本类: 提取 maxLength(int) / format(str) / pattern(str|None) / message
      - 选项类: 提取 allowedValues(list) / message
      - 其余类型: 返回 {} (无约束)
    不做破坏性迁移, 仅做容错, 保证序列化层写入的是干净结构。
    """
    if not isinstance(validation, dict):
        return {}

    message = validation.get('message')
    if not isinstance(message, str):
        message = ''

    if field_type in NUMBER_TYPES:
        out: dict = {'message': message}
        for key in ('min', 'max', 'step'):
            v = _coerce_number(validation.get(key))
            if v is not None:
                out[key] = v
        dec = validation.get('decimals')
        if isinstance(dec, int) and dec >= 0:
            out['decimals'] = dec
        elif isinstance(dec, str) and dec.isdigit():
            out['decimals'] = int(dec)
        # 单位 (unit): 展示用文案, 非法/空时丢弃
        unit = validation.get('unit')
        if isinstance(unit, str) and unit.strip():
            out['unit'] = unit.strip()
        return out

    if field_type in TEXT_MAXLENGTH_TYPES:
        out = {'message': message}
        ml = validation.get('maxLength')
        if isinstance(ml, int) and ml > 0:
            out['maxLength'] = ml
        elif isinstance(ml, str) and ml.isdigit():
            out['maxLength'] = int(ml)
        return out

    if field_type in OPTION_TYPES:
        allowed = validation.get('allowedValues')
        if isinstance(allowed, (list, tuple)):
            allowed = [str(a) for a in allowed if a is not None]
        else:
            allowed = []
        return {'allowedValues': allowed, 'message': message}

    if field_type in DATE_TYPES:
        out = {'message': message}
        for key in ('minDate', 'maxDate'):
            v = validation.get(key)
            if isinstance(v, str) and v.strip():
                out[key] = v.strip()
        return out

    # 其余类型 (EMAIL/PHONE/ID_CARD/BANK_CARD/URL 固有格式, SELECT/MULTISELECT/RICH_TEXT/其他): 无配置项
    return {}


def validate_field_value(field_type: str, validation, value) -> list[str]:
    """对单个字段值按其限制条件做校验, 返回错误文案列表 (空 = 通过)。

    约定:
      - 空值 (None / '' / []) 不做约束校验 (必填由 is_required 另行处理)。
      - 任一规则命中且配置了 message, 优先用 message; 否则用默认文案。
      - 后端权威校验与前端拦截共用本函数逻辑 (前端用等价 TS 实现)。

    Args:
        field_type: DynamicField.FieldType 的字符串值。
        validation: 该字段的 validation 配置 (规范化或松散均可)。
        value: 待校验的值 (文本/数字/列表等)。

    Returns:
        list[str]: 错误信息; 通过时为空列表。
    """
    errors: list[str] = []
    if validation is None or validation == '':
        return errors

    norm = normalize_validation(field_type, validation) if not isinstance(validation, dict) else validation

    # 空值跳过 (必填另算)
    is_empty = value is None or value == '' or (isinstance(value, (list, dict)) and len(value) == 0)
    if is_empty:
        return errors

    msg = (validation.get('message') if isinstance(validation, dict) else '') or ''

    # ---- 数字类 ----
    if field_type in NUMBER_TYPES:
        num = _coerce_number(value)
        if num is None:
            errors.append(msg or '请输入有效的数字')
            return errors
        min_v = _coerce_number(validation.get('min'))
        max_v = _coerce_number(validation.get('max'))
        step = _coerce_number(validation.get('step'))
        decimals = validation.get('decimals')
        if min_v is not None and num < min_v:
            errors.append(msg or f'不能小于 {_fmt_num(min_v)}')
        if max_v is not None and num > max_v:
            errors.append(msg or f'不能大于 {_fmt_num(max_v)}')
        if isinstance(decimals, int) and decimals >= 0:
            # 小数位数 (仅当确有小数时校验)
            if '.' in repr(float(num)):
                actual = len(repr(float(num)).split('.')[1])
                if actual > decimals:
                    errors.append(msg or f'最多保留 {decimals} 位小数')
        if step is not None and step > 0:
            base = min_v if min_v is not None else 0.0
            # 步长校验: (num - base) 应为 step 的整数倍
            if abs((num - base) / step - round((num - base) / step)) > 1e-9:
                errors.append(msg or f'取值需为步长 {_fmt_num(step)} 的整数倍')
        return errors

    # ---- 文本类: 最大字数 (TEXT_MAXLENGTH_TYPES) + 类型层固有格式 (TEXT_WITH_FORMAT_TYPES) ----
    if field_type in TEXT_MAXLENGTH_TYPES or field_type in TEXT_WITH_FORMAT_TYPES:
        text = value if isinstance(value, str) else ('' if value is None else str(value))
        if field_type in TEXT_MAXLENGTH_TYPES:
            max_len = validation.get('maxLength')
            if isinstance(max_len, int) and max_len > 0 and len(text) > max_len:
                errors.append(msg or f'最多输入 {max_len} 个字')
        # 类型层固有格式 (EMAIL/PHONE/ID_CARD/BANK_CARD/URL); 无配置项, 由字段类型直接约束
        fmt = INHERENT_FORMAT.get(field_type)
        if fmt:
            pattern = TEXT_FORMAT_PATTERNS.get(fmt)
            if pattern:
                try:
                    if not re.match(pattern, text):
                        errors.append(msg or _format_hint(fmt))
                except re.error:
                    # 正则非法: 不阻断, 交由前端/配置侧处理
                    pass
        return errors

    # ---- 选项类 (可选范围) ----
    if field_type in OPTION_TYPES:
        allowed = validation.get('allowedValues')
        if isinstance(allowed, (list, tuple)) and allowed:
            allowed_str = {str(a) for a in allowed}
            selected = value if isinstance(value, (list, tuple)) else [value]
            for sel in selected:
                if str(sel) not in allowed_str:
                    errors.append(msg or '取值超出允许范围')
                    break
        return errors

    # ---- 日期类: 日期可选范围 (minDate / maxDate) ----
    if field_type in DATE_TYPES:
        dates = value if isinstance(value, (list, tuple)) else [value]
        lo = _parse_date(validation.get('minDate'))
        hi = _parse_date(validation.get('maxDate'))
        for d in dates:
            dv = _parse_date(d)
            if dv is None:
                # 非法日期值跳过范围校验 (格式问题由必填/类型层另行处理)
                continue
            if lo is not None and dv < lo:
                errors.append(msg or f'不能早于 {validation.get("minDate")}')
                break
            if hi is not None and dv > hi:
                errors.append(msg or f'不能晚于 {validation.get("maxDate")}')
                break
        return errors

    return errors


def _fmt_num(n: float) -> str:
    """数字格式化: 整数去尾零。"""
    if n is None:
        return ''
    if float(n).is_integer():
        return str(int(n))
    return str(n)


def _format_hint(fmt: str) -> str:
    """格式校验失败时的默认文案。"""
    return {
        'EMAIL': '邮箱格式不正确',
        'URL': '链接格式不正确',
        'PHONE': '电话格式不正确',
        'ID_CARD': '身份证号格式不正确',
        'BANK_CARD': '银行卡号格式不正确',
        'CUSTOM': '内容格式不正确',
    }.get(fmt, '内容格式不正确')
