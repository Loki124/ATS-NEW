"""Automation Engine (PRD v4 §11.3 + 02-feature-spec-automation.md)

执行流程：
1. 触发事件 (Stage Entered / State Changed / Evaluation Submitted / Scheduled)
2. 加载所有相关 AutomationRule
3. 按优先级 P0 → P1 → P2 顺序评估
4. 对每条规则：
   - 检查适用范围 (scope)
   - 评估子条件 (AND/OR)
   - 决定执行动作
5. 记录执行日志
6. 失败率告警与熔断

Action 执行：
- AUTO_ADVANCE: 自动推进到下一阶段
- SKIP_TO: 跳过到指定阶段
- REMIND: 发送提醒
- REJECT_TO_POOL: 入公共人才库
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from .models import (
    AutomationLog,
    AutomationRule,
    AutomationRule as Rule,  # alias
)

logger = logging.getLogger(__name__)


@dataclass
class TriggerContext:
    """触发器上下文"""
    trigger_type: str  # STAGE_ENTERED / STATE_CHANGED / EVALUATION_SUBMITTED / SCHEDULED
    candidate_id: str
    application_id: Optional[str] = None
    stage_id: Optional[str] = None
    evaluation_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class RuleMatchResult:
    """规则匹配结果"""
    rule: AutomationRule
    matched: bool
    conditions_detail: List[Dict[str, Any]]
    skip_reason: Optional[str] = None


@dataclass
class ExecutionResult:
    """执行结果"""
    rule_id: str
    rule_name: str
    matched: bool
    action_taken: str
    skip_reason: str = ''
    error_message: str = ''
    execution_ms: int = 0
    log_id: Optional[str] = None


class AutomationEngine:
    """自动化规则引擎"""

    def __init__(self, context: TriggerContext, actor=None):
        self.context = context
        self.actor = actor

    def find_candidate_rules(self) -> List[AutomationRule]:
        """加载候选规则"""
        qs = AutomationRule.objects.filter(
            enabled=True,
            trigger_type=self.context.trigger_type,
            deleted_at__isnull=True,
        )
        # 阶段匹配
        if self.context.stage_id:
            qs = qs.filter(stage_id=self.context.stage_id)
        # 优先级排序
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2}
        rules = list(qs)
        rules.sort(key=lambda r: priority_order.get(r.priority, 99))
        return rules

    def evaluate_rule(self, rule: AutomationRule) -> RuleMatchResult:
        """评估单条规则"""
        conditions_detail = []
        # 1. 适用范围
        if not self._match_scope(rule):
            return RuleMatchResult(
                rule=rule, matched=False,
                conditions_detail=[],
                skip_reason='scope_unmatched',
            )
        # 2. 子条件
        if not self._match_conditions(rule, conditions_detail):
            return RuleMatchResult(
                rule=rule, matched=False,
                conditions_detail=conditions_detail,
                skip_reason='condition_unmatched',
            )
        return RuleMatchResult(
            rule=rule, matched=True,
            conditions_detail=conditions_detail,
        )

    def execute_rule(self, rule: AutomationRule, match_result: RuleMatchResult) -> ExecutionResult:
        """执行规则动作"""
        start = time.time()
        try:
            if rule.action_type == 'AUTO_ADVANCE':
                result = self._action_auto_advance(rule)
            elif rule.action_type == 'SKIP_TO':
                result = self._action_skip_to(rule)
            elif rule.action_type == 'REMIND':
                result = self._action_remind(rule)
            elif rule.action_type == 'REJECT_TO_POOL':
                result = self._action_reject_to_pool(rule)
            else:
                return ExecutionResult(
                    rule_id=rule.id, rule_name=rule.name,
                    matched=True, action_taken='',
                    skip_reason=f'unknown_action_type: {rule.action_type}',
                )

            execution_ms = int((time.time() - start) * 1000)
            result.execution_ms = execution_ms
            self._save_log(rule, match_result, result)
            return result

        except Exception as e:
            execution_ms = int((time.time() - start) * 1000)
            logger.exception('Rule %s execution failed', rule.id)
            result = ExecutionResult(
                rule_id=rule.id, rule_name=rule.name,
                matched=True, action_taken='',
                error_message=str(e),
                execution_ms=execution_ms,
            )
            self._save_log(rule, match_result, result)
            return result

    def run(self) -> List[ExecutionResult]:
        """执行入口：评估所有规则 + 执行动作"""
        rules = self.find_candidate_rules()
        results: List[ExecutionResult] = []

        for rule in rules:
            # 熔断检查
            if self._is_circuit_open(rule):
                results.append(ExecutionResult(
                    rule_id=rule.id, rule_name=rule.name,
                    matched=False, action_taken='',
                    skip_reason='circuit_open',
                ))
                continue

            match = self.evaluate_rule(rule)
            if not match.matched:
                # 不匹配：也记日志（用于调试）
                self._save_log(rule, match, ExecutionResult(
                    rule_id=rule.id, rule_name=rule.name,
                    matched=False, action_taken='',
                    skip_reason=match.skip_reason or '',
                ))
                continue

            # 执行
            exec_result = self.execute_rule(rule, match)
            results.append(exec_result)

        return results

    # ----------------------------------------------------------
    # 内部方法
    # ----------------------------------------------------------
    def _match_scope(self, rule: AutomationRule) -> bool:
        """适用范围匹配"""
        scope = rule.scope_json or {}
        if not scope:
            return True

        # positions 限制
        positions = scope.get('positions', [])
        if positions:
            if not self.context.extra or 'position_id' not in self.context.extra:
                return False
            if self.context.extra['position_id'] not in positions:
                return False

        # priority 限制
        priority = scope.get('priority', [])
        if priority:
            if not self.context.extra or self.context.extra.get('demand_priority') not in priority:
                return False

        # referral_type 限制
        ref_type = scope.get('referral_type', [])
        if ref_type:
            if not self.context.extra or self.context.extra.get('referral_type') not in ref_type:
                return False

        return True

    def _match_conditions(self, rule: AutomationRule, detail: List[Dict]) -> bool:
        """子条件匹配"""
        conditions = rule.condition_json or []
        if not conditions:
            return True

        results = []
        for cond in conditions:
            ok = self._match_single_condition(cond)
            results.append(ok)
            detail.append({
                'field': cond.get('field'),
                'operator': cond.get('operator'),
                'value': cond.get('value'),
                'matched': ok,
            })

        if rule.condition_logic == 'ALL':
            return all(results)
        else:  # ANY
            return any(results)

    def _match_single_condition(self, cond: Dict) -> bool:
        """单条子条件匹配"""
        field = cond.get('field', '')
        op = cond.get('operator', 'EQ')
        value = cond.get('value')
        actual = self._resolve_field_value(field)

        if op == 'EQ':
            return actual == value
        if op == 'NEQ':
            return actual != value
        if op == 'IN':
            return actual in (value or [])
        if op == 'NOT_IN':
            return actual not in (value or [])
        if op == 'GT':
            return actual is not None and actual > value
        if op == 'GTE':
            return actual is not None and actual >= value
        if op == 'LT':
            return actual is not None and actual < value
        if op == 'LTE':
            return actual is not None and actual <= value
        if op == 'IS_EMPTY':
            return actual in (None, '', [])
        if op == 'IS_NOT_EMPTY':
            return actual not in (None, '', [])
        return False

    def _resolve_field_value(self, field: str):
        """解析字段值"""
        ctx = self.context.extra or {}
        # 优先从 context 取
        if field in ctx:
            return ctx[field]
        # 内置字段
        builtin = {
            'candidate_id': self.context.candidate_id,
            'application_id': self.context.application_id,
            'stage_id': self.context.stage_id,
        }
        return builtin.get(field)

    def _is_circuit_open(self, rule: AutomationRule) -> bool:
        """熔断检查：失败率超过阈值则停止执行"""
        threshold = rule.failure_rate_threshold or 0.5
        # 查最近 100 次执行
        recent_logs = AutomationLog.objects.filter(
            rule=rule, deleted_at__isnull=True,
        ).order_by('-trigger_time')[:100]
        if not recent_logs:
            return False
        total = len(recent_logs)
        failed = sum(1 for l in recent_logs if l.evaluate_result == 'ERROR' or l.error_message)
        if total < 10:
            return False  # 样本太少不熔断
        return (failed / total) > threshold

    # ----------------------------------------------------------
    # 动作实现
    # ----------------------------------------------------------
    @transaction.atomic
    def _action_auto_advance(self, rule: AutomationRule) -> ExecutionResult:
        """AUTO_ADVANCE: 自动推进到下一阶段"""
        from apps.application.models import Application, ApplicationStageRecord
        from apps.application.services import advance_application_to_next_stage

        if not self.context.application_id:
            return ExecutionResult(
                rule_id=rule.id, rule_name=rule.name,
                matched=True, action_taken='',
                skip_reason='no_application_id',
            )

        try:
            application = Application.objects.get(id=self.context.application_id)
        except Application.DoesNotExist:
            return ExecutionResult(
                rule_id=rule.id, rule_name=rule.name,
                matched=True, action_taken='',
                skip_reason='application_not_found',
            )

        result = advance_application_to_next_stage(
            application,
            actor=self.actor,
            skip_entry_condition=rule.skip_check,
            reason=f'AUTO_ADVANCE by rule {rule.name}',
        )
        return ExecutionResult(
            rule_id=rule.id, rule_name=rule.name,
            matched=True,
            action_taken=f'advanced to {result.get("next_stage_name", "N/A")}',
        )

    @transaction.atomic
    def _action_skip_to(self, rule: AutomationRule) -> ExecutionResult:
        """SKIP_TO: 跳到指定阶段"""
        from apps.application.models import Application
        from apps.application.services import jump_application_to_stage

        if not rule.next_stage_id:
            return ExecutionResult(
                rule_id=rule.id, rule_name=rule.name,
                matched=True, action_taken='',
                skip_reason='no_target_stage',
            )
        if not self.context.application_id:
            return ExecutionResult(
                rule_id=rule.id, rule_name=rule.name,
                matched=True, action_taken='',
                skip_reason='no_application_id',
            )
        try:
            application = Application.objects.get(id=self.context.application_id)
        except Application.DoesNotExist:
            return ExecutionResult(
                rule_id=rule.id, rule_name=rule.name,
                matched=True, action_taken='',
                skip_reason='application_not_found',
            )

        result = jump_application_to_stage(
            application,
            target_stage_id=rule.next_stage_id,
            actor=self.actor,
            skip_entry_condition=rule.skip_check,
            reason=f'SKIP_TO by rule {rule.name}',
        )
        return ExecutionResult(
            rule_id=rule.id, rule_name=rule.name,
            matched=True,
            action_taken=f'skipped to {result.get("stage_name", "N/A")}',
        )

    @transaction.atomic
    def _action_remind(self, rule: AutomationRule) -> ExecutionResult:
        """REMIND: 发送提醒"""
        from apps.notification.services import send_notification

        recipient_ids = self._resolve_remind_recipients(rule)
        message = (rule.scope_json or {}).get('remind_message', f'请及时处理候选人 {self.context.candidate_id}')

        for rid in recipient_ids:
            send_notification(
                recipient_id=rid,
                title='自动化提醒',
                content=message,
                link=f'/candidates/{self.context.candidate_id}',
                source='AUTOMATION',
                source_id=rule.id,
            )

        return ExecutionResult(
            rule_id=rule.id, rule_name=rule.name,
            matched=True,
            action_taken=f'reminded {len(recipient_ids)} recipients',
        )

    @transaction.atomic
    def _action_reject_to_pool(self, rule: AutomationRule) -> ExecutionResult:
        """REJECT_TO_POOL: 入公共人才库"""
        from apps.talent_pool.services import move_candidate_to_pool

        if not self.context.candidate_id:
            return ExecutionResult(
                rule_id=rule.id, rule_name=rule.name,
                matched=True, action_taken='',
                skip_reason='no_candidate_id',
            )
        result = move_candidate_to_pool(
            candidate_id=self.context.candidate_id,
            entry_source='AUTOMATION',
            entry_reason=f'AUTO by rule {rule.name}',
            actor=self.actor,
        )
        return ExecutionResult(
            rule_id=rule.id, rule_name=rule.name,
            matched=True,
            action_taken=f'moved to pool ({result.get("talent_pool_id", "N/A")})',
        )

    def _resolve_remind_recipients(self, rule: AutomationRule) -> List[str]:
        """解析提醒接收人"""
        scope = rule.scope_json or {}
        recipient_type = scope.get('remind_to', 'CURRENT_HANDLER')

        if recipient_type == 'CURRENT_HANDLER':
            # 找当前处理人
            if self.context.application_id:
                from apps.application.models import Application, ApplicationStageRecord
                try:
                    app = Application.objects.get(id=self.context.application_id)
                    sr = app.current_stage_record
                    if sr and sr.current_handler_id:
                        return [sr.current_handler_id]
                except Exception:
                    pass
        elif recipient_type == 'STAGE_OWNERS':
            return (rule.stage_rule_owner_ids if hasattr(rule, 'stage_rule_owner_ids') else []) or []
        elif recipient_type == 'CUSTOM':
            return scope.get('custom_user_ids', [])

        return []

    def _save_log(self, rule: AutomationRule, match: RuleMatchResult, exec_result: ExecutionResult):
        """持久化执行日志"""
        try:
            log = AutomationLog.objects.create(
                rule=rule,
                candidate_id=self.context.candidate_id,
                trigger_time=timezone.now(),
                evaluate_result='MATCHED' if match.matched else 'UNMATCHED',
                action_taken=exec_result.action_taken[:200] if exec_result.action_taken else '',
                skip_reason=(match.skip_reason or exec_result.skip_reason or '')[:500],
                error_message=exec_result.error_message,
                execution_ms=exec_result.execution_ms,
            )
            exec_result.log_id = log.id
        except Exception as e:
            logger.warning('Failed to save automation log: %s', e)


# ============================================================
# Celery 任务入口
# ============================================================
def run_automation_for_trigger(context: TriggerContext) -> List[ExecutionResult]:
    """便捷函数：在 Celery 任务或同步代码中调用"""
    return AutomationEngine(context).run()
