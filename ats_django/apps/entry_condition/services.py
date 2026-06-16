"""Entry Condition Services (PRD v4 §10)

提供：
- EntryConditionEvaluator: 阶段进入条件规则评估
- 评估流程：先按规则顺序匹配 → 命中返回 PASS/FAIL + reject_message
- 支持单规则内 AND/OR/NOT 表达式
- 记录评估日志
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from apps.candidate.models import Candidate
from apps.process.models import ProcessStageLink, RecruitmentStage
from apps.process.services.expression_service import evaluate_expression

from .models import (
    ConditionFieldType,
    ConditionItem,
    ConditionOperator,
    EntryConditionLog,
    EntryConditionRule,
    EntryConditionRuleStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class ConditionCheckResult:
    """单条条件项评估结果"""
    item_seq: int
    field: str
    operator: str
    value: Any
    passed: bool
    actual_value: Any = None
    error: Optional[str] = None


@dataclass
class RuleEvaluationResult:
    """单条规则评估结果"""
    rule_id: str
    rule_name: str
    rule_seq: int
    passed: bool
    reject_message: str
    item_results: List[ConditionCheckResult]


@dataclass
class StageEntryResult:
    """完整阶段进入评估结果"""
    link_id: str
    stage_id: str
    stage_name: str
    overall_passed: bool
    matched_rule_seq: Optional[int]
    reject_message: str
    rule_results: List[RuleEvaluationResult]


class EntryConditionEvaluator:
    """阶段进入条件评估器

    使用：
        evaluator = EntryConditionEvaluator(link, candidate)
        result = evaluator.evaluate()
    """

    def __init__(self, link: ProcessStageLink, candidate: Candidate, context: Optional[dict] = None):
        self.link = link
        self.candidate = candidate
        self.context = context or {}

    def evaluate(self, save_log: bool = True) -> StageEntryResult:
        """执行评估"""
        rules = self.link.entry_condition_rules.filter(
            status=EntryConditionRuleStatus.ENABLED, deleted_at__isnull=True,
        ).order_by('rule_seq')

        rule_results: List[RuleEvaluationResult] = []
        overall_passed = True
        matched_rule_seq: Optional[int] = None
        reject_message = ''

        # 评估每条启用的规则
        for rule in rules:
            rr = self._evaluate_rule(rule)
            rule_results.append(rr)
            if rr.passed:
                # 命中通过规则 - 允许进入
                if matched_rule_seq is None:
                    matched_rule_seq = rr.rule_seq
                # 短路：任意一条规则通过即放行
                overall_passed = True
                reject_message = ''
                break
            else:
                # 记录拒绝信息（最后一条）
                reject_message = rr.reject_message or reject_message

        # 如果没有规则通过，且规则列表为空，则默认通过
        if not rule_results:
            overall_passed = True
        elif matched_rule_seq is None:
            overall_passed = False

        result = StageEntryResult(
            link_id=self.link.id,
            stage_id=self.link.stage_id,
            stage_name=self.link.stage.name,
            overall_passed=overall_passed,
            matched_rule_seq=matched_rule_seq,
            reject_message=reject_message,
            rule_results=rule_results,
        )

        if save_log:
            self._save_log(result)

        return result

    def _evaluate_rule(self, rule: EntryConditionRule) -> RuleEvaluationResult:
        """评估单条规则"""
        items = rule.items.filter(deleted_at__isnull=True).order_by('item_seq')
        item_results: List[ConditionCheckResult] = []
        condition_results: Dict[int, bool] = {}

        for item in items:
            cr = self._evaluate_item(item)
            item_results.append(cr)
            condition_results[item.item_seq] = cr.passed

        # 规则内求值
        try:
            passed = evaluate_expression(rule.expression, condition_results)
        except Exception as e:
            logger.exception('Rule %s expression evaluation failed: %s', rule.id, e)
            passed = False

        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.rule_name,
            rule_seq=rule.rule_seq,
            passed=passed,
            reject_message=rule.reject_message,
            item_results=item_results,
        )

    def _evaluate_item(self, item: ConditionItem) -> ConditionCheckResult:
        """评估单条条件项"""
        try:
            actual = self._get_actual_value(item)
            passed = self._compare(item.operator, actual, item.value)
            return ConditionCheckResult(
                item_seq=item.item_seq,
                field=item.field,
                operator=item.operator,
                value=item.value,
                passed=passed,
                actual_value=actual,
            )
        except Exception as e:
            logger.exception('Condition item %s evaluation failed: %s', item.id, e)
            return ConditionCheckResult(
                item_seq=item.item_seq,
                field=item.field,
                operator=item.operator,
                value=item.value,
                passed=False,
                error=str(e),
            )

    def _get_actual_value(self, item: ConditionItem) -> Any:
        """获取字段实际值"""
        if item.condition_type == ConditionFieldType.STAGE_STATUS:
            # 阶段条件 - 来自前序阶段记录
            stage_name = item.stage_name
            if not stage_name:
                return None
            return self._get_prior_stage_status(stage_name)

        if item.condition_type == ConditionFieldType.CANDIDATE:
            return self._get_candidate_value(item.field)

        if item.condition_type == ConditionFieldType.DEMAND:
            return self._get_demand_value(item.field)

        return None

    def _get_prior_stage_status(self, stage_name: str) -> Optional[str]:
        """获取前序阶段的状态"""
        from apps.application.models import Application, ApplicationStageRecord
        # 找到申请 + 该阶段的 stage_record
        try:
            application = Application.objects.filter(
                candidate=self.candidate, deleted_at__isnull=True,
            ).first()
            if not application:
                return None
            stage = RecruitmentStage.objects.filter(name=stage_name).first()
            if not stage:
                return None
            sr = ApplicationStageRecord.objects.filter(
                application=application, stage=stage, deleted_at__isnull=True,
            ).first()
            return sr.status if sr else None
        except Exception:
            return None

    def _get_candidate_value(self, field: str) -> Any:
        """获取候选人字段值"""
        mapping = {
            'AGE': self._calc_age(),
            'GENDER': getattr(self.candidate, 'gender', None),
            'HIGHEST_EDU': getattr(self.candidate, 'highest_education', None),
            'WORK_YEARS': getattr(self.candidate, 'work_years', None),
            'CURRENT_CITY': getattr(self.candidate, 'current_city', None),
            'EXPECTED_CITY': getattr(self.candidate, 'expected_city', None),
        }
        return mapping.get(field)

    def _get_demand_value(self, field: str) -> Any:
        """获取需求中字段值（来自职位/部门）"""
        demand = self.context.get('demand')
        if not demand:
            return None
        # 通过 demand 找到关联的 position / department / users
        position = getattr(demand, 'position', None)
        if not position:
            return None
        mapping = {
            'HIRING_MANAGER': getattr(position, 'hiring_manager_id', None),
            'HIRING_MANAGER_SUPER': getattr(position, 'hiring_manager_supervisor_id', None),
            'BU_PRESIDENT': getattr(position, 'bu_president_id', None),
            'SOLID_VP': getattr(position, 'solid_vp_id', None),
            'DOTTED_VP': getattr(position, 'dotted_vp_id', None),
            'DEMAND_LEVEL': getattr(demand, 'demand_level', None),
            'DEPARTMENT': getattr(position, 'department_id', None),
        }
        value = mapping.get(field)
        # 过滤离职人员
        if value and field in ('HIRING_MANAGER', 'HIRING_MANAGER_SUPER', 'BU_PRESIDENT', 'SOLID_VP', 'DOTTED_VP'):
            from apps.core.models import User
            if isinstance(value, list):
                value = [v for v in value if User.objects.filter(id=v, is_active=True).exists()]
            else:
                if not User.objects.filter(id=value, is_active=True).exists():
                    value = None
        return value

    def _calc_age(self) -> Optional[int]:
        """根据身份证号或生日计算年龄"""
        if not self.candidate.birth_date:
            return None
        from datetime import date
        today = date.today()
        born = self.candidate.birth_date
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def _compare(self, op: str, actual: Any, expected: Any) -> bool:
        """比较运算符"""
        try:
            if op == ConditionOperator.EQ:
                return actual == expected
            if op == ConditionOperator.NEQ:
                return actual != expected
            if op == ConditionOperator.GT:
                return actual is not None and actual > expected
            if op == ConditionOperator.GTE:
                return actual is not None and actual >= expected
            if op == ConditionOperator.LT:
                return actual is not None and actual < expected
            if op == ConditionOperator.LTE:
                return actual is not None and actual <= expected
            if op == ConditionOperator.BETWEEN:
                if not isinstance(expected, (list, tuple)) or len(expected) != 2:
                    return False
                return expected[0] <= (actual or 0) <= expected[1]
            if op == ConditionOperator.IN:
                if not isinstance(expected, (list, tuple)):
                    return False
                return actual in expected
            if op == ConditionOperator.NOT_IN:
                if not isinstance(expected, (list, tuple)):
                    return False
                return actual not in expected
            if op == ConditionOperator.IS_EMPTY:
                return actual in (None, '', [], {})
            if op == ConditionOperator.IS_NOT_EMPTY:
                return actual not in (None, '', [], {})
        except Exception as e:
            logger.warning('Comparison failed: %s, %s, %s, %s', op, actual, expected, e)
            return False
        return False

    def _save_log(self, result: StageEntryResult):
        """持久化评估日志"""
        try:
            snapshot = {
                'candidate_id': self.candidate.id,
                'stage_id': self.link.stage_id,
                'link_id': self.link.id,
                'rule_results': [
                    {
                        'rule_id': r.rule_id,
                        'rule_seq': r.rule_seq,
                        'passed': r.passed,
                        'items': [
                            {
                                'item_seq': ir.item_seq,
                                'field': ir.field,
                                'operator': ir.operator,
                                'value': ir.value,
                                'actual_value': ir.actual_value,
                                'passed': ir.passed,
                                'error': ir.error,
                            }
                            for ir in r.item_results
                        ],
                    }
                    for r in result.rule_results
                ],
            }
            EntryConditionLog.objects.create(
                rule_id=result.rule_results[0].rule_id if result.rule_results else self.link.entry_condition_rules.first().id,
                candidate_id=self.candidate.id,
                stage_id=self.link.stage_id,
                link_id=self.link.id,
                passed=result.overall_passed,
                reject_message=result.reject_message,
                snapshot=snapshot,
            )
        except Exception as e:
            logger.warning('Failed to save entry condition log: %s', e)


def evaluate_stage_entry(link: ProcessStageLink, candidate: Candidate, context: Optional[dict] = None) -> StageEntryResult:
    """便捷函数：评估阶段进入条件"""
    return EntryConditionEvaluator(link, candidate, context).evaluate()
