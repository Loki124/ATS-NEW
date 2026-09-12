"""重复候选人规则服务层

三类职责：
1. 配置读写：merge / application 两套单例 JSON 配置（缺失时回退默认值）
2. 规则种子：系统内置规则的幂等补齐 / 重置
3. 规则判定：compare() 给出「两条候选人数据是否命中某条查重规则」的参考实现

⚠️ 边界说明：compare() 目前是**配置侧参考实现**，供单测与前端试算复用，
尚未接入 apps.add_candidate.services.duplicate_check.DuplicateCheckService.find()
的线上链路（接管实时查重属独立改造，需单独拍板，避免影响既有创建候选人流程）。
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

from django.utils import timezone

from .catalog import (
    APPLICATION_CONFIG_KEY,
    DEFAULT_APPLICATION_CONFIG,
    DEFAULT_MERGE_CONFIG,
    DEFAULT_RULES,
    DEFAULT_SYSTEM_RULES,
    FIELD_BY_KEY,
    LOGIC_ALL,
    LOGIC_ANY,
    MERGE_CONFIG_KEY,
)
from .models import DuplicateConfig, DuplicateRule

logger = logging.getLogger(__name__)

# 经历类（复合）查重项 → 参与比对的关键字段
EXPERIENCE_MATCH_KEYS = {
    'education': ('school', 'start_date', 'end_date', 'major'),
    'work_experience': ('company', 'start_date', 'end_date', 'title'),
    'internship': ('company', 'start_date', 'end_date', 'title'),
}

# 字符串型查重项归一化时忽略的分隔符
_SEPARATORS = (' ', '-', '\t')


# ============================================================
# 一、配置读写
# ============================================================
def get_config(key: str, default: Optional[dict] = None) -> dict:
    """读取单例配置，缺失字段用默认值补齐（默认值始终作为基底）。"""
    base = dict(default or {})
    obj = DuplicateConfig.objects.filter(key=key, deleted_at__isnull=True).first()
    if obj and isinstance(obj.config, dict):
        base.update(obj.config)
    return base


def save_config(key: str, config: dict, user=None) -> dict:
    """保存单例配置（整体覆盖）。"""
    obj, _created = DuplicateConfig.objects.get_or_create(key=key)
    obj.config = config
    if user is not None and getattr(user, 'is_authenticated', False):
        obj.updated_by = user
        if not obj.created_by_id:
            obj.created_by = user
    obj.save()
    return obj.config


def patch_config(key: str, partial: dict, default: dict, user=None) -> dict:
    """局部更新单例配置：与默认值和现值做浅合并后落库。"""
    merged = get_config(key, default)
    merged.update(partial or {})
    return save_config(key, merged, user=user)


def get_merge_config() -> dict:
    return get_config(MERGE_CONFIG_KEY, DEFAULT_MERGE_CONFIG)


def get_application_config() -> dict:
    return get_config(APPLICATION_CONFIG_KEY, DEFAULT_APPLICATION_CONFIG)


# ============================================================
# 二、规则种子
# ============================================================
def _create_rules(specs: list[dict]) -> list[DuplicateRule]:
    """按 specs 建规则；DEFAULT_SYSTEM_RULES 中的条目落为系统内置。"""
    system_names = {spec['name'] for spec in DEFAULT_SYSTEM_RULES}
    created: list[DuplicateRule] = []
    for spec in specs:
        created.append(DuplicateRule.objects.create(
            name=spec['name'],
            scope='ALL',
            is_system=spec['name'] in system_names,
            condition_logic=spec['condition_logic'],
            any_count=spec['any_count'],
            items=spec['items'],
            is_enabled=spec['is_enabled'],
            order_index=spec['order_index'],
        ))
    return created


def seed_default_rules() -> list[DuplicateRule]:
    """首次初始化：仅当表内**无存活规则**时种入完整默认集合（系统 2 条 + 预置 3 条）。

    刻意不做「按名补齐」：非空表若继续补齐，用户删掉的预置规则会在下次读取时复活，
    形成"删不掉"的假象。需要恢复默认请显式调用 :func:`reset_rules`。
    """
    if DuplicateRule.objects.filter(deleted_at__isnull=True).exists():
        return []
    created = _create_rules(DEFAULT_RULES)
    logger.info('[duplicate_rule] 首次初始化默认规则 %d 条', len(created))
    return created


def reset_rules() -> list[DuplicateRule]:
    """恢复默认：软删全部存活规则（含用户自定义），再种入完整默认集合。

    返回重置后的存活规则列表。
    """
    DuplicateRule.objects.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
    _create_rules(DEFAULT_RULES)
    return list(
        DuplicateRule.objects.filter(deleted_at__isnull=True).order_by('order_index', 'id')
    )


def list_rules(scope: Optional[str] = None) -> list[DuplicateRule]:
    """列出规则；scope 仅用于筛选「全局 + 指定范围」，None 表示不过滤。"""
    qs = DuplicateRule.objects.all()
    if scope:
        qs = qs.filter(scope__in=['ALL', scope])
    return list(qs.order_by('order_index', 'id'))


# ============================================================
# 三、规则判定（参考实现）
# ============================================================
def _normalize_scalar(value: Any) -> str:
    text = '' if value is None else str(value)
    for sep in _SEPARATORS:
        text = text.replace(sep, '')
    return text.strip().lower()


def _normalize_experience(key: str, entries: Any) -> tuple[frozenset, ...]:
    """把经历列表归一化为可比较的元组集合（仅保留该查重项的关键字段）。"""
    if not isinstance(entries, (list, tuple)):
        return ()
    fields = EXPERIENCE_MATCH_KEYS.get(key, ())
    normalized = []
    for entry in entries:
        if isinstance(entry, dict):
            normalized.append(tuple(_normalize_scalar(entry.get(f)) for f in fields))
        else:
            normalized.append((_normalize_scalar(entry),))
    return tuple(normalized)


def normalize_field(key: str, value: Any):
    """按查重项类型归一化取值（标量 vs 经历复合）。"""
    if key in EXPERIENCE_MATCH_KEYS:
        return _normalize_experience(key, value)
    return _normalize_scalar(value)


def field_matches(key: str, left: Any, right: Any) -> bool:
    """单个查重项是否一致。

    - 标量项：忽略空格 / 连字符 / 大小写后相等
    - 经历项：任一条目关键字段完全一致即视为该查重项一致
    - 任一侧为空 → 视为不一致（避免空值造成误判重复）
    """
    if left in (None, '', [], {}) or right in (None, '', [], {}):
        return False
    if key in EXPERIENCE_MATCH_KEYS:
        left_set = set(normalize_field(key, left))
        right_set = set(normalize_field(key, right))
        if not left_set or not right_set:
            return False
        return bool(left_set & right_set)
    return normalize_field(key, left) == normalize_field(key, right)


def rule_matches(rule: DuplicateRule, left: dict, right: dict) -> dict:
    """判定单条规则是否命中，返回命中详情。"""
    items = rule.items or []
    hit_keys: list[str] = []
    miss_keys: list[str] = []
    for item in items:
        key = item.get('key') if isinstance(item, dict) else item
        if not key:
            continue
        if field_matches(key, left.get(key), right.get(key)):
            hit_keys.append(key)
        else:
            miss_keys.append(key)

    if rule.condition_logic == LOGIC_ANY:
        matched = len(hit_keys) >= max(1, int(rule.any_count or 1))
    elif rule.condition_logic == LOGIC_ALL:
        matched = bool(items) and not miss_keys
    else:  # pragma: no cover - choices 已限制，保留兜底
        matched = False

    return {
        'rule_id': rule.id,
        'rule_name': rule.name,
        'matched': matched,
        'hit_keys': hit_keys,
        'miss_keys': miss_keys,
        'hit_labels': [FIELD_BY_KEY[k]['label'] for k in hit_keys if k in FIELD_BY_KEY],
    }


def compare(left: dict, right: dict, rules: Optional[Iterable[DuplicateRule]] = None) -> dict:
    """比较两条候选人数据，返回命中的启用规则。

    仅使用 is_enabled=True 的规则；rules 显式传入时可覆盖该过滤。
    """
    rule_list = list(rules) if rules is not None else list_rules()
    rule_list = [r for r in rule_list if r.is_enabled]

    results = [rule_matches(rule, left, right) for rule in rule_list]
    hits = [r for r in results if r['matched']]
    return {
        'is_duplicate': bool(hits),
        'matched_rules': hits,
        'evaluated_rules': len(rule_list),
        'detail': results,
    }


def rule_condition_text(rule: DuplicateRule) -> str:
    """规则列表「查重条件」列文案：全部 / 任意 N 项。"""
    if rule.condition_logic == LOGIC_ANY:
        return f'任意 {max(1, int(rule.any_count or 1))} 项'
    if rule.condition_logic == LOGIC_ALL:
        return '全部'
    return '全部'


def rule_items_text(rule: DuplicateRule) -> list[str]:
    """规则列表「查重项」列的展示文案（按 catalog 顺序输出 label）。"""
    keys = [
        item.get('key') if isinstance(item, dict) else item
        for item in (rule.items or [])
    ]
    labels = [FIELD_BY_KEY[k]['label'] for k in keys if k in FIELD_BY_KEY]
    return labels
