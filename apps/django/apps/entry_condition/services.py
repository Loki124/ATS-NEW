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


# 进入条件中「候选人字段」legacy 键 → AtomicMetric.source_path 的映射。
# 这是当前唯一已存在的指标层（apps/metrics.AtomicMetric）接入点；其它来源
# （DEMAND / STAGE_STATUS）暂不在本次范围。
#
# 工作流（2026-10-01 接入）：
#   _get_candidate_value 先按此表把 legacy 键转为 source_path，再走 AtomicMetric +
#   candidate_snapshot + FieldResolverRegistry 解析；
#   解析失败回退到 _LEGACY_CANDIDATE_FALLBACK（保留旧字段直查语义），确保现网行为零变化。
#
# 新增候选人字段时只需：
#   1) 在此表加一行 source_path
#   2) 同时在 _LEGACY_CANDIDATE_FALLBACK 加一行 getattr 兜底
#   3) 在 AtomicMetric 中由 0009/0010 迁移自动 seed（或手工建）
#   即可——前端目录、评估取值、指标定义 三处统一收口。
LEGACY_CANDIDATE_FIELD_TO_PATH = {
    'AGE': 'candidate.age',
    'GENDER': 'candidate.gender',
    'HIGHEST_EDU': 'candidate.highest_education',
    'WORK_YEARS': 'candidate.work_years',
    'CURRENT_CITY': 'candidate.current_city',
    'EXPECTED_CITY': 'candidate.expected_city',
}

# legacy 硬编码兜底（指标未 seed / 快照无该字段时使用，绝不 500）。
_LEGACY_CANDIDATE_FALLBACK = {
    'AGE': lambda c: _calc_age_from_birth_date(c),
    'GENDER': lambda c: getattr(c, 'gender', None),
    'HIGHEST_EDU': lambda c: getattr(c, 'highest_education', None),
    'WORK_YEARS': lambda c: getattr(c, 'work_years', None),
    'CURRENT_CITY': lambda c: getattr(c, 'current_city', None),
    'EXPECTED_CITY': lambda c: getattr(c, 'expected_city', None),
}


def _calc_age_from_birth_date(candidate: Candidate) -> Optional[int]:
    """按身份证 / 生日计算年龄（legacy _calc_age 等价语义）。"""
    if not getattr(candidate, 'birth_date', None):
        return None
    from datetime import date
    today = date.today()
    born = candidate.birth_date
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


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
        from django.conf import settings
        # Phase 3（2026-08-31）委托开关：RULE_ENGINE_DISPATCH=True 时改走统一规则引擎
        # 派发（复用统一 ConditionEvaluator / ScopeMatcher / 动作执行器），结果翻译回
        # legacy 形态；默认 False → 维持原 entry_condition 引擎路径，现网行为零变化。
        # 任何异常均回退到 legacy 求值，确保委托路径出现故障也不影响现网。
        if getattr(settings, 'RULE_ENGINE_DISPATCH', False):
            try:
                unified_result = self._run_via_unified_engine(save_log)
                if unified_result is not None:
                    return unified_result
            except Exception:  # noqa: BLE001 — RULE_ENGINE dispatch 失败必须降级到 legacy, 否则主流程断
                logger.exception(
                    'RULE_ENGINE dispatch failed for entry_condition; fallback to legacy'
                )

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

    def _run_via_unified_engine(self, save_log: bool) -> Optional[StageEntryResult]:
        """委托到统一规则引擎执行（RULE_ENGINE_DISPATCH=True 时）。

        把 entry_condition 的 (link, candidate, context) 翻译为统一引擎的 EvaluationContext，
        过滤 source_app='entry_condition' 的镜像规则（ScopeMatcher 已按 link_id 过滤），
        复用已注册的 ALLOW 执行器完成「命中即放行」标记，再把统一 ExecutionResult 翻译回
        legacy 的 StageEntryResult 形态。

        Returns:
            StageEntryResult；若该 link 无任何镜像规则（双写尚未覆盖）返回 None，
            由调用方回退到 legacy 求值，避免「静默放行」。
        """
        from apps.rule_engine.integrations.entry_condition_executors import (
            register_entry_condition_executors,
        )
        from apps.rule_engine.models import Rule
        from apps.rule_engine.services import EvaluationContext, RuleEngine

        register_entry_condition_executors()

        # 1) 把 legacy 条件涉及的字段实际值塞进 context.extra，供统一 ConditionEvaluator
        #    求值（统一引擎不内置 entry_condition 的领域字段解析，复用本 evaluator 的解析）。
        extra = self._build_dispatch_extra()
        extra['candidate_id'] = self.candidate.id

        ctx = EvaluationContext(
            trigger_type='STAGE_ENTERED',
            candidate_id=self.candidate.id,
            stage_id=self.link.stage_id,
            link_id=self.link.id,
            process_id=self.link.process_id,
            extra=extra,
        )

        # 2) 仅派发 entry_condition 家族的镜像规则
        results = RuleEngine().dispatch(ctx, source_app='entry_condition')
        if not results:
            # 无镜像规则：回退 legacy（避免双写覆盖缺口被静默放过）
            return None

        # 3) 翻译：任一规则命中 → 放行（取最小 rule_seq 作为 matched_rule_seq）；
        #    未命中 → 拦截，reject_message 取末条未命中规则的提示。
        matched_rule_seq: Optional[int] = None
        reject_message = ''
        for r in results:
            unified_rule = Rule.objects.filter(id=r.rule_id).first()
            if unified_rule is None:
                continue
            rule_seq = unified_rule.config_json.get('rule_seq')
            if r.matched:
                if matched_rule_seq is None:
                    matched_rule_seq = rule_seq
            else:
                reject_message = unified_rule.config_json.get('reject_message') or reject_message

        overall_passed = matched_rule_seq is not None

        result = StageEntryResult(
            link_id=self.link.id,
            stage_id=self.link.stage_id,
            stage_name=self.link.stage.name,
            overall_passed=overall_passed,
            matched_rule_seq=matched_rule_seq,
            reject_message=reject_message,
            rule_results=[],  # dispatch 路径不重建逐条 item 明细（已写入统一执行日志）
        )

        if save_log:
            self._save_log(result)
        return result

    def _build_dispatch_extra(self) -> Dict[str, Any]:
        """收集本 link 下所有启用规则涉及字段的实际值，填入 dispatch context.extra。

        复用本 evaluator 已有的领域字段解析（_get_actual_value），保证与 legacy 求值
        语义一致。同名跨规则字段以末次解析为准（阶段状态类字段若存在同名冲突，属已知
        边界，统一引擎侧仅按 field 名取单值）。
        """
        extra: Dict[str, Any] = {}
        rules = self.link.entry_condition_rules.filter(
            status=EntryConditionRuleStatus.ENABLED, deleted_at__isnull=True,
        )
        for rule in rules:
            for item in rule.items.filter(deleted_at__isnull=True).order_by('item_seq'):
                try:
                    extra[item.field] = self._get_actual_value(item)
                except Exception as e:  # noqa: BLE001 — 单条解析失败不应阻断整次派发
                    logger.warning('进入条件单条解析失败 item_seq=%s field=%s err=%s', item.item_seq, item.field, e, exc_info=True)
                    continue
        return extra

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
        except Exception as e:  # noqa: BLE001 — DSL 表达式可能抛任意业务异常 (NameError/自定义), 降级 passed=False 而非阻断整规则
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
        except Exception as e:  # noqa: BLE001 — 单条条件项可能因指标层/字段缺失抛多种异常, 降级 passed=False 而非阻断整规则
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
        except Exception:  # noqa: BLE001 — ORM 查询兜底返 None (字段不存在/数据缺失), 不阻断规则评估
            return None

    def _get_candidate_value(self, field: str) -> Any:
        """获取候选人字段值。

        解析优先级：
            a. 指标库解析 —— 按 LEGACY_CANDIDATE_FIELD_TO_PATH 把 legacy 键转 到
               AtomicMetric.source_path，再走 candidate_snapshot + FieldResolverRegistry
               取值（与 metrics 指标层共享路径解析）。
            b. legacy 兜底 —— 当指标未定义 / 解析失败时，落 _LEGACY_CANDIDATE_FALLBACK
               直查 ORM 字段，确保现网行为零变化。

        不抛异常：解析失败 = None（与原语义一致，触发 IS_EMPTY / 数值 GT 等为 False）。
        """
        source_path = LEGACY_CANDIDATE_FIELD_TO_PATH.get(field)
        if source_path:
            try:
                from apps.metrics.models import AtomicMetric
                from apps.metrics.services.candidate_snapshot import build_candidate_snapshot
                from apps.metrics.services.field_resolver import (
                    FieldResolverRegistry,
                    FieldResolveError,
                )

                # 仅按 source_path 命中即视为「指标已接」——不再要求 name=field。
                # 这样既兼容既有迁移（name=年龄）也兼容未来运营把指标改名/重命名。
                metric = AtomicMetric.objects.filter(
                    source_path=source_path, status='enabled', deleted_at__isnull=True,
                ).first()
                if metric is not None:
                    snapshot = build_candidate_snapshot(self.candidate.id)
                    return FieldResolverRegistry.resolve(source_path, snapshot)
            except Exception as e:  # noqa: BLE001 — 任何指标层异常都不阻断 legacy 兜底
                logger.warning(
                    'entry_condition metrics 解析失败 field=%s path=%s err=%s',
                    field, source_path, e,
                )

        fallback = _LEGACY_CANDIDATE_FALLBACK.get(field)
        if fallback is not None:
            try:
                return fallback(self.candidate)
            except Exception:  # noqa: BLE001 — legacy 兜底字段解析失败返 None, 不阻断主流程
                return None
        return None

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
        except (TypeError, ValueError) as e:
            # Python 比较运算符窄集: 类型不匹配 (None > 5) / 不可哈希 (unhashable in list).
            # 业务规则 DSL 抛出的其他异常应外抛以便发现真实 bug.
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
        except Exception as e:  # noqa: BLE001 — 审计落库失败不应阻断主结果 (用户看到规则通过/拒绝即可)
            logger.warning('Failed to save entry condition log: %s', e)


def evaluate_stage_entry(link: ProcessStageLink, candidate: Candidate, context: Optional[dict] = None) -> StageEntryResult:
    """便捷函数：评估阶段进入条件"""
    return EntryConditionEvaluator(link, candidate, context).evaluate()
