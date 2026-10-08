"""统一规则引擎 —— 只读适配器层（Phase 1）。

把 6 个 legacy 规则源只读呈现为统一的 ``UnifiedRuleDTO``，供 ``/api/v1/rule-engine/rules/``
聚合列出。适配器是纯函数式映射（无副作用、无 DB 写），绝不改动任何 legacy 模型/写路径。

映射依据：docs/rule-engine/UNIFIED_RULE_ENGINE_DESIGN.md §2.2 / §3.1。

各源软删/启用语义（聚合时按各自约定过滤）：
- automation / entry_condition / time_limit：继承 SoftDeleteModel → deleted_at__isnull=True
  - automation / time_limit 另有 enabled 布尔
  - entry_condition 用 status(ENABLED/DISABLED)
- campus_control（ControlRule）：硬删 + is_active 布尔
- mou（MouRule）：无软删 + is_active 布尔
- field_acl（FieldACL）：无软删/启用字段 → 全量呈现（enabled=True）
"""
from __future__ import annotations

import decimal
from dataclasses import dataclass, field
from typing import Any, Dict, List

from apps.automation.models import AutomationRule
from apps.campus_control.models import ControlRule
from apps.entry_condition.models import EntryConditionRule
from apps.field_acl.models import FieldACL
from apps.mou.models import MouRule
from apps.time_limit.models import TimeLimitRule

from .models import (
    ConditionType,
    RuleCategory,
    RuleStatus,
    UnifiedActionType,
    UnifiedTriggerType,
)


@dataclass
class UnifiedRuleDTO:
    """统一规则 DTO（对齐 Rule 模型字段 + 溯源/摘要）。

    仅用于只读展示，不进 DB。出参经 CamelCaseJSONRenderer 自动转驼峰。
    """

    id: str
    name: str
    category: str
    source_app: str
    trigger_type: str
    legacy_model: str
    legacy_id: str
    # 可选/派生字段
    trigger_timing: str | None = None
    scope_json: Dict[str, Any] = field(default_factory=dict)
    priority: str = 'P1'
    priority_rank: int = 0
    status: str = RuleStatus.ENABLED
    enabled: bool = True
    condition_expression: str = ''
    condition_logic: str = 'ALL'
    config_json: Dict[str, Any] = field(default_factory=dict)
    conditions_summary: List[Dict[str, Any]] = field(default_factory=list)
    actions_summary: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'yes', 'enabled')
    return bool(value)


def _conditions_from_list(items, default_type: str = ConditionType.CUSTOM) -> List[Dict[str, Any]]:
    """把 list[dict] 形式的原子条件转为 summary 列表。"""
    out: List[Dict[str, Any]] = []
    if not items:
        return out
    for i, c in enumerate(items, start=1):
        if isinstance(c, dict):
            out.append({
                'seq': i,
                'condition_type': c.get('condition_type', default_type),
                'field': c.get('field'),
                'operator': c.get('operator'),
                'value': c.get('value'),
            })
        else:
            out.append({
                'seq': i,
                'condition_type': getattr(c, 'condition_type', default_type),
                'field': getattr(c, 'field', None),
                'operator': getattr(c, 'operator', None),
                'value': getattr(c, 'value', None),
            })
    return out


def _get_items(rule):
    """兼容 manager（真实模型）与 list（测试 SimpleNamespace）。"""
    items = getattr(rule, 'items', None)
    if items is None:
        return []
    if hasattr(items, 'all'):
        return list(items.all())
    return list(items)


def _norm_decimal(value):
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value


# ---------------------------------------------------------------------------
# 适配器
# ---------------------------------------------------------------------------

class AutomationAdapter:
    """automation.AutomationRule → category=TCA。"""

    legacy_model = 'apps.automation.AutomationRule'

    def to_unified(self, legacy) -> UnifiedRuleDTO:
        conditions = _conditions_from_list(getattr(legacy, 'condition_json', []) or [], ConditionType.CUSTOM)
        action_type = getattr(legacy, 'action_type', None)
        actions = [{
            'seq': 1,
            'action_type': action_type,
            'params': {
                'next_stage_id': getattr(legacy, 'next_stage_id', None),
                'skip_check': getattr(legacy, 'skip_check', False),
            },
        }] if action_type else []
        enabled = _as_bool(getattr(legacy, 'enabled', True))
        return UnifiedRuleDTO(
            id=legacy.id,
            name=getattr(legacy, 'name', ''),
            category=RuleCategory.TCA,
            source_app='automation',
            trigger_type=getattr(legacy, 'trigger_type', ''),
            legacy_model=self.legacy_model,
            legacy_id=legacy.id,
            trigger_timing=getattr(legacy, 'trigger_timing', None),
            scope_json=getattr(legacy, 'scope_json', {}) or {},
            priority=getattr(legacy, 'priority', 'P1'),
            priority_rank=0,
            status=RuleStatus.ENABLED if enabled else RuleStatus.DISABLED,
            enabled=enabled,
            condition_expression='',
            condition_logic=getattr(legacy, 'condition_logic', 'ALL') or 'ALL',
            config_json={},
            conditions_summary=conditions,
            actions_summary=actions,
        )


class EntryConditionAdapter:
    """entry_condition.EntryConditionRule → category=TCA, trigger=STAGE_ENTERED。"""

    legacy_model = 'apps.entry_condition.EntryConditionRule'

    def to_unified(self, legacy) -> UnifiedRuleDTO:
        items = _get_items(legacy)
        conditions = _conditions_from_list(items, ConditionType.CUSTOM)
        # 把 item_seq 作为 seq（expression 引用 item_seq）
        for c, item in zip(conditions, items):
            c['seq'] = getattr(item, 'item_seq', c['seq'])
            c['condition_type'] = getattr(item, 'condition_type', ConditionType.CUSTOM)

        enabled = str(getattr(legacy, 'status', RuleStatus.ENABLED)) == RuleStatus.ENABLED
        return UnifiedRuleDTO(
            id=legacy.id,
            name=getattr(legacy, 'rule_name', ''),
            category=RuleCategory.TCA,
            source_app='entry_condition',
            trigger_type=UnifiedTriggerType.STAGE_ENTERED,
            legacy_model=self.legacy_model,
            legacy_id=legacy.id,
            trigger_timing=None,
            scope_json={'process': getattr(legacy, 'process_id', None)} if getattr(legacy, 'process_id', None) else {},
            priority='P1',
            priority_rank=getattr(legacy, 'rule_seq', 0),
            status=RuleStatus.ENABLED if enabled else RuleStatus.DISABLED,
            enabled=enabled,
            condition_expression=getattr(legacy, 'expression', '') or '',
            condition_logic=getattr(legacy, 'match_type', 'ALL') or 'ALL',
            config_json={'reject_message': getattr(legacy, 'reject_message', ''),
                         'match_type': getattr(legacy, 'match_type', 'ALL')},
            # 命中即 ALLOW；未命中 REJECT（reject_message 已入 config_json）
            actions_summary=[{'seq': 1, 'action_type': UnifiedActionType.ALLOW, 'params': {}}],
            conditions_summary=conditions,
        )


class TimeLimitAdapter:
    """time_limit.TimeLimitRule → category=TCA, trigger=STAGE_DWELL_TIMEOUT, action=LOCK。"""

    legacy_model = 'apps.time_limit.TimeLimitRule'

    def to_unified(self, legacy) -> UnifiedRuleDTO:
        conditions = _conditions_from_list(getattr(legacy, 'conditions', []) or [], ConditionType.CUSTOM)
        enabled = _as_bool(getattr(legacy, 'enabled', True))
        lock_duration = getattr(legacy, 'lock_duration', None)
        extension = getattr(legacy, 'extension_per_person', 0)
        eff_scope = getattr(legacy, 'effective_scope', 'NEW_ONLY')
        return UnifiedRuleDTO(
            id=legacy.id,
            name=getattr(legacy, 'rule_name', ''),
            category=RuleCategory.TCA,
            source_app='time_limit',
            trigger_type=UnifiedTriggerType.STAGE_DWELL_TIMEOUT,
            legacy_model=self.legacy_model,
            legacy_id=legacy.id,
            trigger_timing=None,
            scope_json={'process': getattr(legacy, 'process_id', None)} if getattr(legacy, 'process_id', None) else {},
            priority='P1',
            priority_rank=getattr(legacy, 'priority', 0),
            status=RuleStatus.ENABLED if enabled else RuleStatus.DISABLED,
            enabled=enabled,
            condition_expression='',
            condition_logic='ALL',
            config_json={
                'lock_duration': lock_duration,
                'extension_per_person': extension,
                'effective_scope': eff_scope,
            },
            actions_summary=[{
                'seq': 1,
                'action_type': UnifiedActionType.LOCK,
                'params': {
                    'lock_duration': lock_duration,
                    'extension_per_person': extension,
                    'effective_scope': eff_scope,
                },
            }],
            conditions_summary=conditions,
        )


class ConstraintAdapter:
    """campus_control.ControlRule → category=CONSTRAINT, trigger=OFFER_SUBMITTED。

    领域模型：conditions/actions 留空，target/strength/dimension/indicator 进 config_json。
    """

    legacy_model = 'apps.campus_control.ControlRule'

    def to_unified(self, legacy) -> UnifiedRuleDTO:
        enabled = _as_bool(getattr(legacy, 'is_active', True))
        dimension = getattr(legacy, 'dimension', None)
        indicator = getattr(legacy, 'indicator', None)
        return UnifiedRuleDTO(
            id=legacy.id,
            name=getattr(legacy, 'code', '') or f"{getattr(legacy, 'id', '')}",
            category=RuleCategory.CONSTRAINT,
            source_app='campus_control',
            trigger_type=UnifiedTriggerType.OFFER_SUBMITTED,
            legacy_model=self.legacy_model,
            legacy_id=legacy.id,
            trigger_timing=None,
            # 标准 scope 结构：bu/position/level
            scope_json={
                'bu': getattr(legacy, 'bu', '') or None,
                'position': getattr(legacy, 'position', '') or None,
                'level': getattr(legacy, 'level', '') or None,
            },
            priority='P1',
            priority_rank=0,
            status=RuleStatus.ENABLED if enabled else RuleStatus.DISABLED,
            enabled=enabled,
            condition_expression='',
            condition_logic='ALL',
            config_json={
                'target': _norm_decimal(getattr(legacy, 'target', None)),
                'strength': getattr(legacy, 'strength', None),
                'dimension': getattr(dimension, 'name', None) if dimension else None,
                'indicator': getattr(indicator, 'name', None) if indicator else None,
                'year': getattr(legacy, 'year', None),
                'annual_target': getattr(legacy, 'annual_target', 0),
            },
            conditions_summary=[],
            actions_summary=[],
        )


class MouAdapter:
    """mou.MouRule → category=TCA, trigger=BUSINESS_EVENT。

    原始 trigger_event 存 config_json.event；conditions/actions 为 JSON dict 时整体进 config_json。
    """

    legacy_model = 'apps.mou.MouRule'

    def to_unified(self, legacy) -> UnifiedRuleDTO:
        enabled = _as_bool(getattr(legacy, 'is_active', True))
        conditions = getattr(legacy, 'conditions', {}) or {}
        actions = getattr(legacy, 'actions', {}) or {}
        cond_summary: List[Dict[str, Any]] = []
        act_summary: List[Dict[str, Any]] = []
        if isinstance(conditions, list):
            cond_summary = _conditions_from_list(conditions, ConditionType.CUSTOM)
        if isinstance(actions, list):
            for i, a in enumerate(actions, start=1):
                if isinstance(a, dict):
                    act_summary.append({
                        'seq': i,
                        'action_type': a.get('action_type'),
                        'params': a.get('params', a),
                    })
        return UnifiedRuleDTO(
            id=legacy.id,
            name=getattr(legacy, 'name', ''),
            category=RuleCategory.TCA,
            source_app='mou',
            trigger_type=UnifiedTriggerType.BUSINESS_EVENT,
            legacy_model=self.legacy_model,
            legacy_id=legacy.id,
            trigger_timing=None,
            scope_json={},
            priority='P1',
            priority_rank=0,
            status=RuleStatus.ENABLED if enabled else RuleStatus.DISABLED,
            enabled=enabled,
            condition_expression='',
            condition_logic='ALL',
            config_json={
                'event': getattr(legacy, 'trigger_event', None),
                'conditions': conditions if not isinstance(conditions, list) else None,
                'actions': actions if not isinstance(actions, list) else None,
            },
            conditions_summary=cond_summary,
            actions_summary=act_summary,
        )


class PolicyAdapter:
    """field_acl.FieldACL → category=POLICY, trigger 留空, action=SET_PERMISSION。"""

    legacy_model = 'apps.field_acl.FieldACL'

    def to_unified(self, legacy) -> UnifiedRuleDTO:
        return UnifiedRuleDTO(
            id=legacy.id,
            name=f"{getattr(legacy, 'entity', '')}.{getattr(legacy, 'field', '')}",
            category=RuleCategory.POLICY,
            source_app='field_acl',
            trigger_type='',
            legacy_model=self.legacy_model,
            legacy_id=legacy.id,
            trigger_timing=None,
            scope_json={},
            priority='P1',
            priority_rank=0,
            status=RuleStatus.ENABLED,
            enabled=True,
            condition_expression='',
            condition_logic='ALL',
            config_json={
                'entity': getattr(legacy, 'entity', None),
                'field': getattr(legacy, 'field', None),
                'role_code': getattr(legacy, 'role_code', None),
                'permission': getattr(legacy, 'permission', None),
            },
            actions_summary=[{
                'seq': 1,
                'action_type': UnifiedActionType.SET_PERMISSION,
                'params': {
                    'entity': getattr(legacy, 'entity', None),
                    'field': getattr(legacy, 'field', None),
                    'role_code': getattr(legacy, 'role_code', None),
                    'permission': getattr(legacy, 'permission', None),
                },
            }],
            conditions_summary=[],
        )


# ---------------------------------------------------------------------------
# 聚合
# ---------------------------------------------------------------------------

def aggregate_rules(filters: Dict[str, Any] | None = None) -> List[UnifiedRuleDTO]:
    """聚合 6 个 legacy 源为统一 DTO 列表，并按可选 filters 过滤。

    filters 支持：category / trigger_type / enabled(bool|str) / source_app。
    """
    filters = filters or {}
    dtos: List[UnifiedRuleDTO] = []

    for legacy in AutomationRule.objects.filter(deleted_at__isnull=True):
        dtos.append(AutomationAdapter().to_unified(legacy))
    for legacy in EntryConditionRule.objects.filter(deleted_at__isnull=True, status=RuleStatus.ENABLED):
        dtos.append(EntryConditionAdapter().to_unified(legacy))
    for legacy in TimeLimitRule.objects.filter(deleted_at__isnull=True, enabled=True):
        dtos.append(TimeLimitAdapter().to_unified(legacy))
    for legacy in ControlRule.objects.filter(is_active=True):
        dtos.append(ConstraintAdapter().to_unified(legacy))
    for legacy in MouRule.objects.filter(is_active=True):
        dtos.append(MouAdapter().to_unified(legacy))
    for legacy in FieldACL.objects.all():
        dtos.append(PolicyAdapter().to_unified(legacy))

    # 过滤
    cat = filters.get('category')
    if cat is not None:
        dtos = [d for d in dtos if d.category == cat]
    tt = filters.get('trigger_type')
    if tt is not None:
        dtos = [d for d in dtos if d.trigger_type == tt]
    sa = filters.get('source_app')
    if sa is not None:
        dtos = [d for d in dtos if d.source_app == sa]
    en = filters.get('enabled')
    if en is not None:
        want = _as_bool(en)
        dtos = [d for d in dtos if d.enabled == want]

    return dtos
