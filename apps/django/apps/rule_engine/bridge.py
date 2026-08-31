"""统一规则引擎 —— 双写镜像桥（Phase 2，2026-08-31）。

本模块把 legacy 业务记录（当前仅 automation）以「幂等 upsert」方式镜像成统一
``Rule`` / 执行日志 ``RuleExecutionLog``，供后续 Phase 的只读聚合 / 委托派发使用。

设计要点（见 docs/rule-engine/UNIFIED_RULE_ENGINE_DESIGN.md §3.2 / §6 Phase 2）：
- 仅新增写入统一表，绝不回写 legacy 表、绝不改现网行为。
- 镜像必须幂等：以 (source_app, legacy_id) 定位统一记录，重复调用结果与一次一致。
- 镜像链路 best-effort：调用方（signals / 管理命令）负责吞掉异常仅记日志；本模块
  内部不再吞异常，便于一致性校验命令精确暴露问题。
- 避免循环依赖：automation 仅在函数体内懒加载（类型注解用字符串）；rule_engine 侧
  不 import 任何业务 app 的模块级符号。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .models import (
    Action,
    Condition,
    ConditionType,
    EvaluateResult,
    Rule,
    RuleCategory,
    RuleExecutionLog,
    RuleStatus,
    UnifiedActionType,
)

logger = logging.getLogger(__name__)

# automation.AutomationRule 在统一表中的来源标记（与 adapters.py 保持一致）
AUTOMATION_SOURCE_APP = 'automation'
AUTOMATION_LEGACY_MODEL = 'automation.AutomationRule'


def _to_bool(value: Any) -> bool:
    return bool(value)


def _build_action_params(rule: Any) -> Dict[str, Any]:
    """从 AutomationRule 拼装统一 Action 的 params_json。

    固定搬运 next_stage_id / skip_check；scope_json 里的提醒字段（remind_to /
    remind_message / custom_user_ids）若存在也一并搬入，供 Remind 执行器复用。
    """
    params: Dict[str, Any] = {
        'next_stage_id': rule.next_stage_id,
        'skip_check': _to_bool(rule.skip_check),
    }
    scope = rule.scope_json or {}
    if 'remind_to' in scope:
        params['remind_to'] = scope['remind_to']
    if 'remind_message' in scope:
        params['remind_message'] = scope['remind_message']
    if 'custom_user_ids' in scope:
        params['custom_user_ids'] = scope['custom_user_ids']
    return params


def sync_automation_rule_to_unified(rule: Any) -> Rule:
    """幂等地把一条 AutomationRule 镜像成统一 Rule（含 conditions / actions 重建）。

    Args:
        rule: automation.models.AutomationRule 实例（调用方已确保未软删或已软删均可）。

    Returns:
        对应的统一 Rule 实例。

    幂等性保证：
    - 以 (source_app='automation', legacy_id=rule.id) 做 update_or_create；
    - 每次都先删后建该 Rule 下的 conditions / actions，因此重复同步不会产生脏数据。
    软删传播：rule.deleted_at 非空 → 对该统一 Rule 也 soft_delete()。
    """
    # 1) 头信息 upsert
    unified, _created = Rule.objects.update_or_create(
        source_app=AUTOMATION_SOURCE_APP,
        legacy_id=rule.id,
        defaults=dict(
            name=rule.name,
            category=RuleCategory.TCA,
            legacy_model=AUTOMATION_LEGACY_MODEL,
            trigger_type=rule.trigger_type,
            trigger_timing=rule.trigger_timing,
            trigger_delay_hours=rule.trigger_delay_hours,
            scope_json=rule.scope_json or {},
            priority=rule.priority,
            priority_rank=0,
            status=RuleStatus.ENABLED if _to_bool(rule.enabled) else RuleStatus.DISABLED,
            enabled=_to_bool(rule.enabled),
            failure_rate_threshold=rule.failure_rate_threshold,
            condition_expression='',
            condition_logic=rule.condition_logic,
            config_json={
                'process_id': str(rule.process_id),
                'stage_id': str(rule.stage_id),
            },
            created_by=rule.created_by,
            updated_by=rule.updated_by,
        ),
    )

    # 2) 条件项：删后重建（seq = index + 1，condition_type 统一为 CUSTOM）
    unified.conditions.all().delete()
    for idx, cond in enumerate(rule.condition_json or []):
        Condition.objects.create(
            rule=unified,
            seq=idx + 1,
            condition_type=ConditionType.CUSTOM,
            field=cond.get('field', ''),
            operator=cond.get('operator', 'EQ'),
            value=cond.get('value'),
        )

    # 3) 动作项：删后重建 1 条（action_type 直接同值映射）
    unified.actions.all().delete()
    Action.objects.create(
        rule=unified,
        seq=1,
        action_type=rule.action_type,
        params_json=_build_action_params(rule),
        enabled=True,
    )

    # 4) 软删传播：legacy 已软删 → 统一侧也软删（幂等：已软删则跳过）
    if rule.deleted_at and unified.deleted_at is None:
        unified.soft_delete()

    return unified


def sync_automation_log_to_unified(log: Any) -> Optional[RuleExecutionLog]:
    """best-effort 把一条 AutomationLog 镜像成统一 RuleExecutionLog。

    仅做单向追加镜像（日志不幂等去重，避免与 automation 侧日志耦合）；统一侧
    rule 字段允许为 None（AutomationLog.rule 已被硬删时）。

    Returns:
        创建的 RuleExecutionLog 实例；异常由调用方吞掉，本函数不抛。
    """
    # 反查对应的统一 Rule（可能不存在，此时 rule 记 None，分类仍按 TCA）
    unified_rule: Optional[Rule] = Rule.objects.filter(
        source_app=AUTOMATION_SOURCE_APP,
        legacy_id=log.rule_id,
    ).first()

    trigger_type = unified_rule.trigger_type if unified_rule else (
        log.rule.trigger_type if log.rule_id and getattr(log, 'rule', None) else ''
    )

    return RuleExecutionLog.objects.create(
        rule=unified_rule,
        rule_category=RuleCategory.TCA,
        trigger_type=trigger_type,
        candidate_id=log.candidate_id,
        evaluate_result=log.evaluate_result,
        action_taken=(log.action_taken or '')[:200],
        skip_reason=((log.skip_reason or '')[:200] or None),
        error_message=(log.error_message or None),
        execution_ms=log.execution_ms,
    )
