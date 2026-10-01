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
from django.db import IntegrityError, OperationalError
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

from .models import (
    Action,
    Condition,
    ConditionLogic,
    ConditionType,
    EvaluateResult,
    Priority,
    Rule,
    RuleCategory,
    RuleExecutionLog,
    RuleStatus,
    UnifiedActionType,
    UnifiedTriggerType,
)

logger = logging.getLogger(__name__)

# automation.AutomationRule 在统一表中的来源标记（与 adapters.py 保持一致）
AUTOMATION_SOURCE_APP = 'automation'
AUTOMATION_LEGACY_MODEL = 'automation.AutomationRule'

# entry_condition / time_limit 在统一表中的来源标记（Phase 3，2026-08-31）
ENTRY_CONDITION_SOURCE_APP = 'entry_condition'
ENTRY_CONDITION_LEGACY_MODEL = 'entry_condition.EntryConditionRule'
TIME_LIMIT_SOURCE_APP = 'time_limit'
TIME_LIMIT_LEGACY_MODEL = 'time_limit.TimeLimitRule'

# campus_control / mou 在统一表中的来源标记（Phase 4，2026-09-01）
CAMPUS_CONTROL_SOURCE_APP = 'campus_control'
CAMPUS_CONTROL_LEGACY_MODEL = 'campus_control.ControlRule'
MOU_SOURCE_APP = 'mou'
MOU_LEGACY_MODEL = 'mou.MouRule'


def _to_bool(value: Any) -> bool:
    return bool(value)


def _norm_decimal(value: Any) -> Any:
    """Decimal → float，便于写入 JSONField（与 adapters.ConstraintAdapter 一致）。"""
    import decimal
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value


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
    # 兼容两种 V1 condition_json 形态：
    #   - dict: {field, operator, value}  —— entry_condition/原 V1 三元组
    #   - str:   "stage.state == PROCESSING"  —— load_process_templates.py:225 把
    #           condition 字符串包成 [str]；bridge 不解析表达式语义（避免歧义），
    #           整体塞到 meta_json.expression 留待 evaluator 自定义解释。
    unified.conditions.all().delete()
    for idx, cond in enumerate(rule.condition_json or []):
        if isinstance(cond, dict):
            field = cond.get('field', '') or ''
            operator = cond.get('operator', 'EQ') or 'EQ'
            value = cond.get('value')
            meta: dict = {}
        elif isinstance(cond, str):
            field = ''
            operator = 'EQ'
            value = None
            meta = {'expression': cond, 'legacy_format': 'string'}
        else:
            logger.warning(
                'sync_automation_rule_to_unified: 跳过非 dict/str 条件 '
                '(idx=%d, type=%s, value=%r)', idx, type(cond).__name__, cond,
            )
            continue
        Condition.objects.create(
            rule=unified,
            seq=idx + 1,
            condition_type=ConditionType.CUSTOM,
            field=field,
            operator=operator,
            value=value,
            meta_json=meta,
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


# ===========================================================================
# Phase 3（2026-08-31）：entry_condition / time_limit 双写镜像
# 设计依据：docs/rule-engine/UNIFIED_RULE_ENGINE_DESIGN.md §3.3 / §3.4 / §6 Phase 3
# - entry_condition：隐式「进入阶段时评估」→ trigger STAGE_ENTERED；
#   命中任一规则即放行（Action ALLOW），否则拦截 + reject_message（由 legacy wrapper 翻译）。
# - time_limit：隐式「阶段停留超时 / 进入时计算锁定」→ trigger STAGE_DWELL_TIMEOUT；
#   conditions 默认 AND；Action LOCK（lock_duration / extension_per_person / effective_scope）。
# 幂等 / 软删传播 / best-effort 语义与 sync_automation_rule_to_unified 完全一致。
# ===========================================================================

def sync_entry_condition_rule_to_unified(rule: Any) -> Rule:
    """幂等地把一条 EntryConditionRule 镜像成统一 Rule（含 conditions / actions 重建）。

    Args:
        rule: entry_condition.models.EntryConditionRule 实例（已软删或未软删均可）。

    Returns:
        对应的统一 Rule 实例。

    映射要点：
    - trigger_type = STAGE_ENTERED；category = TCA。
    - condition_expression 直接搬运 rule.expression（引用 ConditionItem.item_seq）；
      condition_logic 兜底为 rule.match_type（ALL/ANY），与 legacy 求值语义一致。
    - 每条 ConditionItem → Condition（seq=item_seq，condition_type/field/operator/value
      原样搬运，仅搬运未软删的项）。
    - Action：固定 1 条 ALLOW（命中即放行）；reject_message 冗余存入 params_json 与
      config_json，供 legacy 委托 wrapper 在「未命中」时翻译为 REJECT 提示。
    - priority_rank = rule.rule_seq，保证多规则按 link 内顺序进入引擎排序。
    - 软删传播：rule.deleted_at 非空 → 统一侧也 soft_delete()。
    """
    # 懒导入 legacy 状态枚举，避免模块级循环依赖
    from apps.entry_condition.models import EntryConditionRuleStatus

    is_enabled = (rule.status == EntryConditionRuleStatus.ENABLED)
    condition_logic = (
        rule.match_type if rule.match_type in ('ALL', 'ANY') else ConditionLogic.ALL
    )

    unified, _created = Rule.objects.update_or_create(
        source_app=ENTRY_CONDITION_SOURCE_APP,
        legacy_id=rule.id,
        defaults=dict(
            name=rule.rule_name,
            category=RuleCategory.TCA,
            legacy_model=ENTRY_CONDITION_LEGACY_MODEL,
            trigger_type=UnifiedTriggerType.STAGE_ENTERED,
            trigger_timing=None,
            trigger_delay_hours=None,
            scope_json={
                'link_id': str(rule.link_id),
                'process_id': rule.process_id,
            },
            priority=Priority.P1,
            priority_rank=rule.rule_seq,
            status=RuleStatus.ENABLED if is_enabled else RuleStatus.DISABLED,
            enabled=is_enabled,
            failure_rate_threshold=0.5,
            condition_expression=rule.expression or '',
            condition_logic=condition_logic,
            config_json={
                'link_id': str(rule.link_id),
                'process_id': rule.process_id,
                'workflow_version': rule.workflow_version,
                'rule_seq': rule.rule_seq,
                'reject_message': rule.reject_message,
                'match_type': rule.match_type,
            },
            created_by=rule.created_by,
            updated_by=rule.updated_by,
        ),
    )

    # 条件项：仅搬运未软删的项，删后重建（seq = item_seq，与 expression 引用一致）
    unified.conditions.all().delete()
    for item in rule.items.filter(deleted_at__isnull=True).order_by('item_seq'):
        Condition.objects.create(
            rule=unified,
            seq=item.item_seq,
            condition_type=item.condition_type,
            field=item.field,
            operator=item.operator,
            value=item.value,
            stage_name=item.stage_name or None,
            stage_statuses=item.stage_statuses,
            auto_filter_inactive_users=item.auto_filter_inactive_users,
        )

    # 动作项：固定 1 条 ALLOW；reject_message 冗余存入 params_json
    unified.actions.all().delete()
    Action.objects.create(
        rule=unified,
        seq=1,
        action_type=UnifiedActionType.ALLOW,
        params_json={'reject_message': rule.reject_message},
        enabled=True,
    )

    # 软删传播
    if rule.deleted_at and unified.deleted_at is None:
        unified.soft_delete()

    return unified


def sync_entry_condition_log_to_unified(log: Any) -> Optional[RuleExecutionLog]:
    """best-effort 把一条 EntryConditionLog 镜像成统一 RuleExecutionLog。

    单向追加镜像（日志不幂等去重）；evaluate_result 映射：passed→ALLOWED，
    否则→REJECTED（统一枚举见 EvaluateResult）。统一侧 rule 字段允许为 None。
    """
    unified_rule: Optional[Rule] = Rule.objects.filter(
        source_app=ENTRY_CONDITION_SOURCE_APP,
        legacy_id=log.rule_id,
    ).first()

    evaluate_result = (
        EvaluateResult.ALLOWED if getattr(log, 'passed', False) else EvaluateResult.REJECTED
    )
    action_taken = 'allowed' if getattr(log, 'passed', False) else (
        f'rejected: {log.reject_message}'[:200]
    )

    return RuleExecutionLog.objects.create(
        rule=unified_rule,
        rule_category=RuleCategory.TCA,
        trigger_type=UnifiedTriggerType.STAGE_ENTERED,
        candidate_id=log.candidate_id,
        stage_id=log.stage_id,
        link_id=log.link_id,
        evaluate_result=evaluate_result,
        action_taken=action_taken,
        execution_ms=None,
    )


def sync_time_limit_rule_to_unified(rule: Any) -> Rule:
    """幂等地把一条 TimeLimitRule 镜像成统一 Rule（含 conditions / actions 重建）。

    Args:
        rule: time_limit.models.TimeLimitRule 实例（已软删或未软删均可）。

    Returns:
        对应的统一 Rule 实例。

    映射要点：
    - trigger_type = STAGE_DWELL_TIMEOUT；category = TCA。
    - conditions 为内联 JSON 数组（默认 AND）→ Condition 列表（seq=idx+1，
      condition_type=CUSTOM）。
    - Action：固定 1 条 LOCK，params_json 搬运 lock_duration / extension_per_person /
      effective_scope；引擎 LOCK 执行器据此写入 Application.stage_deadline。
    - priority_rank = rule.priority（time_limit 的 int 优先级），priority 取默认 P1。
    - 软删传播：rule.deleted_at 非空 → 统一侧也 soft_delete()。
    """
    unified, _created = Rule.objects.update_or_create(
        source_app=TIME_LIMIT_SOURCE_APP,
        legacy_id=rule.id,
        defaults=dict(
            name=rule.rule_name,
            category=RuleCategory.TCA,
            legacy_model=TIME_LIMIT_LEGACY_MODEL,
            trigger_type=UnifiedTriggerType.STAGE_DWELL_TIMEOUT,
            trigger_timing=None,
            trigger_delay_hours=None,
            scope_json={
                'link_id': str(rule.link_id),
                'process_id': rule.process_id,
            },
            priority=Priority.P1,
            priority_rank=rule.priority,
            status=RuleStatus.ENABLED if _to_bool(rule.enabled) else RuleStatus.DISABLED,
            enabled=_to_bool(rule.enabled),
            failure_rate_threshold=0.5,
            condition_expression='',
            condition_logic=ConditionLogic.ALL,
            config_json={
                'link_id': str(rule.link_id),
                'process_id': rule.process_id,
                'workflow_version': rule.workflow_version,
            },
            created_by=rule.created_by,
            updated_by=rule.updated_by,
        ),
    )

    # 条件项：内联 JSON 数组，删后重建（seq = idx+1）
    unified.conditions.all().delete()
    for idx, cond in enumerate(rule.conditions or []):
        Condition.objects.create(
            rule=unified,
            seq=idx + 1,
            condition_type=ConditionType.CUSTOM,
            field=cond.get('field', ''),
            operator=cond.get('operator', 'EQ'),
            value=cond.get('value'),
        )

    # 动作项：固定 1 条 LOCK
    unified.actions.all().delete()
    Action.objects.create(
        rule=unified,
        seq=1,
        action_type=UnifiedActionType.LOCK,
        params_json={
            'lock_duration': rule.lock_duration,
            'extension_per_person': rule.extension_per_person,
            'effective_scope': rule.effective_scope,
        },
        enabled=True,
    )

    # 软删传播
    if rule.deleted_at and unified.deleted_at is None:
        unified.soft_delete()

    return unified


# ===========================================================================
# Phase 4（2026-09-01）：campus_control / mou 双写镜像
# 设计依据：docs/rule-engine/UNIFIED_RULE_ENGINE_DESIGN.md §3.5 / §3.6 / §6 Phase 4
# - campus_control：CONSTRAINT 家族，保留领域模型 + ConstraintAdapter；统一侧以
#   Rule(category=CONSTRAINT, trigger=OFFER_SUBMITTED) 呈现；校验仍委派 campus calc，
#   占比数学不塞入 TCA 表（D3）。action 按 strength 映射 BLOCK_HARD / BLOCK_SOFT。
# - mou：原生 TCA 家族，trigger=BUSINESS_EVENT，action=SET_PERMISSION；conditions/actions
#   为 JSON dict 时整体进 config_json（与 MouAdapter 读路径一致）。
# 幂等 / best-effort 语义与前述完全一致。campus_control 用硬删 + is_active，无软删；
# 软删传播由 signals.post_delete 统一处理（见各 app signals.py）。
# ===========================================================================

def sync_control_rule_to_unified(rule: Any) -> Rule:
    """幂等地把一条 ControlRule 镜像成统一 Rule（CONSTRAINT 家族）。

    Args:
        rule: campus_control.models.ControlRule 实例（硬删 + is_active；deleted_at 恒空）。

    Returns:
        对应的统一 Rule 实例。

    映射要点：
    - category = CONSTRAINT；trigger_type = OFFER_SUBMITTED。
    - scope_json 标准结构：bu / position / level（与 ConstraintAdapter 一致）。
    - 无结构化条件（占比数学在 campus calc），故 conditions 留空；action 1 条按
      strength 映射 BLOCK_HARD（硬约束）/ BLOCK_SOFT（软约束），params_json 携带
      strength + target 等冗余字段供执行器/日志使用。
    - enabled 反映 is_active；status 同步。软删传播在 post_delete 信号中处理。
    """
    is_enabled = _to_bool(getattr(rule, 'is_active', True))
    strength = getattr(rule, 'strength', '')
    action_type = (
        UnifiedActionType.BLOCK_HARD if strength == '硬约束' else UnifiedActionType.BLOCK_SOFT
    )
    dimension = getattr(rule, 'dimension', None)
    indicator = getattr(rule, 'indicator', None)

    unified, _created = Rule.objects.update_or_create(
        source_app=CAMPUS_CONTROL_SOURCE_APP,
        legacy_id=rule.id,
        defaults=dict(
            name=rule.code or str(rule.id),
            category=RuleCategory.CONSTRAINT,
            legacy_model=CAMPUS_CONTROL_LEGACY_MODEL,
            trigger_type=UnifiedTriggerType.OFFER_SUBMITTED,
            trigger_timing=None,
            trigger_delay_hours=None,
            scope_json={
                'bu': getattr(rule, 'bu', '') or None,
                'position': getattr(rule, 'position', '') or None,
                'level': getattr(rule, 'level', '') or None,
            },
            priority=Priority.P1,
            priority_rank=0,
            status=RuleStatus.ENABLED if is_enabled else RuleStatus.DISABLED,
            enabled=is_enabled,
            failure_rate_threshold=0.5,
            condition_expression='',
            condition_logic=ConditionLogic.ALL,
            config_json={
                'target': _norm_decimal(getattr(rule, 'target', None)),
                'strength': strength,
                'dimension': getattr(dimension, 'name', None) if dimension else None,
                'indicator': getattr(indicator, 'name', None) if indicator else None,
                'year': getattr(rule, 'year', None),
                'annual_target': getattr(rule, 'annual_target', 0),
            },
            created_by=rule.created_by,
            updated_by=rule.updated_by,
        ),
    )

    # 条件项：CONSTRAINT 无结构化条件，留空（占比数学在 campus calc）
    unified.conditions.all().delete()

    # 动作项：1 条 BLOCK_HARD / BLOCK_SOFT
    unified.actions.all().delete()
    Action.objects.create(
        rule=unified,
        seq=1,
        action_type=action_type,
        params_json={
            'strength': strength,
            'target': _norm_decimal(getattr(rule, 'target', None)),
            'annual_target': getattr(rule, 'annual_target', 0),
        },
        enabled=True,
    )

    return unified


def sync_mou_rule_to_unified(rule: Any) -> Rule:
    """幂等地把一条 MouRule 镜像成统一 Rule（TCA 家族，BUSINESS_EVENT）。

    Args:
        rule: mou.models.MouRule 实例（无软删 + is_active；硬删由 signals 处理）。

    Returns:
        对应的统一 Rule 实例。

    映射要点：
    - category = TCA；trigger_type = BUSINESS_EVENT；原始 trigger_event 进 config_json.event。
    - conditions 若为 list[dict] → 重建 Condition 列表（seq=idx+1，CUSTOM）；否则留空。
    - 动作固定 1 条 SET_PERMISSION，params_json 搬运原始 actions（JSON dict/list），
      供 MouActionExecutor 自行解析（与 MouAdapter 读路径一致）。
    """
    is_enabled = _to_bool(getattr(rule, 'is_active', True))
    conditions = getattr(rule, 'conditions', {}) or {}
    actions = getattr(rule, 'actions', {}) or {}

    unified, _created = Rule.objects.update_or_create(
        source_app=MOU_SOURCE_APP,
        legacy_id=rule.id,
        defaults=dict(
            name=getattr(rule, 'name', ''),
            category=RuleCategory.TCA,
            legacy_model=MOU_LEGACY_MODEL,
            trigger_type=UnifiedTriggerType.BUSINESS_EVENT,
            trigger_timing=None,
            trigger_delay_hours=None,
            scope_json={},
            priority=Priority.P1,
            priority_rank=0,
            status=RuleStatus.ENABLED if is_enabled else RuleStatus.DISABLED,
            enabled=is_enabled,
            failure_rate_threshold=0.5,
            condition_expression='',
            condition_logic=ConditionLogic.ALL,
            config_json={
                'event': getattr(rule, 'trigger_event', None),
                'conditions': conditions if not isinstance(conditions, list) else None,
                'actions': actions if not isinstance(actions, list) else None,
            },
            created_by=None,
            updated_by=None,
        ),
    )

    # 条件项：仅当 conditions 为 list 时重建（seq=idx+1）
    unified.conditions.all().delete()
    if isinstance(conditions, list):
        for idx, cond in enumerate(conditions):
            if isinstance(cond, dict):
                Condition.objects.create(
                    rule=unified,
                    seq=idx + 1,
                    condition_type=ConditionType.CUSTOM,
                    field=cond.get('field', ''),
                    operator=cond.get('operator', 'EQ'),
                    value=cond.get('value'),
                )

    # 动作项：固定 1 条 SET_PERMISSION（承载原始 actions 供执行器解析）
    unified.actions.all().delete()
    Action.objects.create(
        rule=unified,
        seq=1,
        action_type=UnifiedActionType.SET_PERMISSION,
        params_json={'actions': actions},
        enabled=True,
    )

    return unified


def mirror_campus_offer_validation(
    candidate_id: Optional[str],
    blocks: Optional[list] = None,
    warnings: Optional[list] = None,
) -> int:
    """best-effort 把一次 campus Offer 校验事件镜像进统一 RuleExecutionLog。

    每条命中（block / warning）记一行，FK 反查对应统一 Rule（campus_control 镜像）。
    纯追加可观测日志，异常吞掉，绝不影响 Offer 钩子主流程。返回写入条数。

    Args:
        candidate_id: 候选人定位。
        blocks / warnings: campus validate_offer_against_rules 返回的命中明细列表，
            每项含 'rule_id'（ControlRule.id）/ 'strength' / 'code' 等。
    """
    written = 0
    for entry in (blocks or []) + (warnings or []):
        try:
            rule_id = entry.get('rule_id')
            unified_rule = (
                Rule.objects.filter(
                    source_app=CAMPUS_CONTROL_SOURCE_APP, legacy_id=rule_id,
                ).first()
                if rule_id else None
            )
            is_block = (entry.get('strength') == '硬约束')
            RuleExecutionLog.objects.create(
                rule=unified_rule,
                rule_category=RuleCategory.CONSTRAINT,
                trigger_type=UnifiedTriggerType.OFFER_SUBMITTED,
                candidate_id=candidate_id,
                evaluate_result=(
                    EvaluateResult.BLOCKED if is_block else EvaluateResult.REJECTED
                ),
                action_taken=(
                    f"{'blocked' if is_block else 'warned'}: "
                    f"{entry.get('code', '')} {entry.get('dimension', '')}·{entry.get('indicator', '')}"
                )[:200],
                action_type=(
                    UnifiedActionType.BLOCK_HARD if is_block else UnifiedActionType.BLOCK_SOFT
                ),
                skip_reason=None,
            )
            written += 1
        except (OperationalError, IntegrityError, ValueError) as e:  # 镜像失败不影响现网
            logger.warning('rule_engine 镜像写失败: %s', e, exc_info=True)
            continue
    return written
