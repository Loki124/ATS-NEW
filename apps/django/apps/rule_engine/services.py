"""统一规则引擎 —— 求值层骨架（Phase 0）。

本模块是 Phase 0 的核心：ConditionEvaluator / ScopeMatcher / ActionExecutorRegistry /
RuleEngine 全部为「可用骨架」，复用 apps.process.services.expression_service 作为唯一
条件求值底座（禁止再造，见设计文档 §1.1 / §2.3）。

Phase 0 边界（硬约束）：
- 字段解析仅覆盖 context.extra 与已知 id 字段（candidate/application/stage/link/process）；
  完整 family 解析（阶段状态、候选人属性、需求属性等）在后续 Phase 接入。
- ActionExecutor 仅提供基类与注册表；具体执行器在后续 Phase 实现。未实现的类型执行器
  显式 raise NotImplementedError("Phase 0 skeleton — 实现于 Phase 2+")，避免「假实现」。
- 不接入任何现有业务调用方；RuleEngine.dispatch 仅被单测驱动。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from apps.process.services.expression_service import (
    evaluate_expression,
    extract_ids,
    validate_expression,
)

from .models import (
    Condition,
    EvaluateResult,
    Rule,
    RuleExecutionLog,
    RuleStatus,
    UnifiedOperator,
)

# 已知 id 字段 <-> EvaluationContext 属性
_KNOWN_ID_FIELDS = {
    'candidate_id',
    'application_id',
    'stage_id',
    'link_id',
    'process_id',
}


@dataclass
class EvaluationContext:
    """一次规则派发的上下文。

    Phase 0 字段解析来源：extra 字典 + 已知 id 字段。后续 Phase 各 family 适配器负责把
    领域对象（候选人/需求/阶段）填充进 extra。
    """
    trigger_type: str
    candidate_id: Optional[str] = None
    application_id: Optional[str] = None
    stage_id: Optional[str] = None
    link_id: Optional[str] = None
    process_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    # Phase 2：委托派发时透传触发人（User 实例），供业务执行器（如自动推进）复用。
    actor: Optional[Any] = None


@dataclass
class ActionResult:
    """单个动作的执行结果。"""
    success: bool
    action_type: str
    message: str = ''
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """单条规则在一次 dispatch 中的结果。"""
    rule_id: str
    matched: bool
    action_results: List[ActionResult] = field(default_factory=list)
    log_id: Optional[str] = None


class ActionExecutor:
    """动作执行器接口（Phase 0 骨架）。

    具体执行器在后续 Phase 实现（AUTO_ADVANCE / SKIP_TO / LOCK / ALLOW ...）。
    基类方法默认 raise NotImplementedError，避免「假实现」误导调用方。
    """

    def supports(self, action_type: str) -> bool:
        """是否支持该 action_type。"""
        raise NotImplementedError("Phase 0 skeleton — 实现于 Phase 2+")

    def execute(self, context: EvaluationContext, action: 'Action', rule: Rule) -> ActionResult:
        """执行动作。"""
        raise NotImplementedError("Phase 0 skeleton — 实现于 Phase 2+")


class ActionExecutorRegistry:
    """动作执行器注册表（开闭原则）。

    dispatch 时按注册顺序找到第一个 supports(action_type) 为真的执行器派发；
    若无匹配执行器，显式 raise NotImplementedError（Phase 0 尚未实现该类型）。
    """

    def __init__(self):
        self._executors: List[ActionExecutor] = []

    def register(self, executor: ActionExecutor) -> None:
        self._executors.append(executor)

    def dispatch(self, context: EvaluationContext, action: 'Action', rule: Rule) -> ActionResult:
        for executor in self._executors:
            try:
                if executor.supports(action.action_type):
                    return executor.execute(context, action, rule)
            except NotImplementedError:
                # 基类/未实现执行器：继续查找下一个
                continue
        raise NotImplementedError(
            f"Phase 0 skeleton — 未注册动作执行器: {action.action_type} (实现于 Phase 2+)"
        )


# 引擎级全局注册表（后续 Phase 的 executors 在此注册）
action_registry = ActionExecutorRegistry()


class ConditionEvaluator:
    """条件求值器（§2.3）。

    Phase 0 边界：字段值仅从 context.extra / 已知 id 字段解析；IS_EMPTY/IS_NOT_EMPTY
    不读 value；BETWEEN 从 meta_json 读 min/max；IN/NOT_IN 用 value 列表。
    """

    # 比较型运算符（actual 为 None 时直接判不命中，避免 TypeError）
    _COMPARE_OPS = {
        UnifiedOperator.EQ,
        UnifiedOperator.NEQ,
        UnifiedOperator.GT,
        UnifiedOperator.GTE,
        UnifiedOperator.LT,
        UnifiedOperator.LTE,
    }

    def evaluate(self, rule: Rule, context: EvaluationContext):
        """遍历 rule.ordered_conditions 求值。

        Returns:
            (final_bool, detail)
            detail = {
              'seq_results': {seq: bool},
              'per_condition': [...],
              'expression': str|None,
              'logic': str,
              'final': bool,
            }
        """
        seq_results: Dict[int, bool] = {}
        per_condition: List[Dict[str, Any]] = []

        for cond in rule.ordered_conditions:
            actual = self._resolve_value(cond, context)
            matched = self._compare(cond, actual)
            seq_results[cond.seq] = matched
            per_condition.append({
                'seq': cond.seq,
                'condition_type': cond.condition_type,
                'field': cond.field,
                'operator': cond.operator,
                'expected': self._expected_repr(cond),
                'actual': actual,
                'matched': matched,
            })

        # 组合：优先用 condition_expression；否则按 condition_logic 兜底
        expression = rule.condition_expression.strip() if rule.condition_expression else ''
        if expression:
            # 复用 expression_service（§1.1/§2.3）：校验 + 提取编号 + 求值
            validation = validate_expression(expression, max_id=len(seq_results))
            if not validation.valid:
                detail = {
                    'seq_results': seq_results,
                    'per_condition': per_condition,
                    'expression': expression,
                    'logic': rule.condition_logic,
                    'final': False,
                    'expression_error': validation.error,
                }
                return False, detail
            used_ids = extract_ids(expression)
            # 仅取表达式引用的 seq 结果参与组合（避免缺失 seq 触发 KeyError）
            final = evaluate_expression(
                expression, {sid: seq_results.get(sid, False) for sid in used_ids}
            )
        else:
            results = list(seq_results.values())
            if rule.condition_logic == 'ANY':
                final = any(results) if results else False
            else:  # ALL（默认）
                final = all(results) if results else False

        detail = {
            'seq_results': seq_results,
            'per_condition': per_condition,
            'expression': expression or None,
            'logic': rule.condition_logic,
            'final': final,
        }
        return final, detail

    # --- 内部辅助 ---

    def _resolve_value(self, cond: Condition, context: EvaluationContext):
        """从 context 解析字段实际值（Phase 0：extra + 已知 id）。"""
        field_name = cond.field
        if field_name in _KNOWN_ID_FIELDS:
            return getattr(context, field_name, None)
        return context.extra.get(field_name)

    def _expected_repr(self, cond: Condition):
        if cond.operator in (UnifiedOperator.BETWEEN,):
            meta = cond.meta_json or {}
            return {'min': meta.get('min'), 'max': meta.get('max')}
        if cond.operator in (UnifiedOperator.IN, UnifiedOperator.NOT_IN):
            return cond.value
        if cond.operator in (UnifiedOperator.IS_EMPTY, UnifiedOperator.IS_NOT_EMPTY):
            return None
        return cond.value

    def _compare(self, cond: Condition, actual: Any) -> bool:
        op = cond.operator

        if op == UnifiedOperator.IS_EMPTY:
            return self._is_empty(actual)
        if op == UnifiedOperator.IS_NOT_EMPTY:
            return not self._is_empty(actual)
        if op == UnifiedOperator.BETWEEN:
            meta = cond.meta_json or {}
            try:
                lo = meta.get('min')
                hi = meta.get('max')
                if actual is None or lo is None or hi is None:
                    return False
                return lo <= actual <= hi
            except TypeError:
                return False
        if op in (UnifiedOperator.IN, UnifiedOperator.NOT_IN):
            values = cond.value if isinstance(cond.value, (list, tuple, set)) else []
            hit = actual in values
            return hit if op == UnifiedOperator.IN else (not hit)
        if op in self._COMPARE_OPS:
            if actual is None:
                return False
            try:
                if op == UnifiedOperator.EQ:
                    return actual == cond.value
                if op == UnifiedOperator.NEQ:
                    return actual != cond.value
                if op == UnifiedOperator.GT:
                    return actual > cond.value
                if op == UnifiedOperator.GTE:
                    return actual >= cond.value
                if op == UnifiedOperator.LT:
                    return actual < cond.value
                if op == UnifiedOperator.LTE:
                    return actual <= cond.value
            except TypeError:
                return False
        # 未知运算符：Phase 0 不实现，保守判不命中
        return False

    @staticmethod
    def _is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ''
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False


class ScopeMatcher:
    """Scope 匹配器（§2.6）。

    逐维度判等：维度为空/None/空列表 → 视为匹配所有；否则 context 对应值需命中。
    Phase 0 支持的维度：bu / position / level / positions / priority / stages / process /
    referral_type / departments（标准 scope 结构见 §2.6）。
    """

    # 标量维度（相等匹配）
    _SCALAR_DIMS = ('bu', 'position', 'level', 'process')
    # 列表维度（context 值命中集合即可）
    _LIST_DIMS = ('positions', 'priority', 'stages', 'referral_type', 'departments')

    @classmethod
    def matches(cls, scope_json: Optional[dict], context: EvaluationContext) -> bool:
        if not scope_json:
            return True
        for dim in cls._SCALAR_DIMS:
            expected = scope_json.get(dim)
            if expected is None or expected == '':
                continue
            actual = cls._resolve_dim(dim, context)
            if actual != expected:
                return False
        for dim in cls._LIST_DIMS:
            expected = scope_json.get(dim)
            if not expected:  # None / 空列表 / 空串
                continue
            if not isinstance(expected, (list, tuple, set)):
                expected = [expected]
            actual = cls._resolve_dim(dim, context)
            if actual is None:
                return False
            if isinstance(actual, (list, tuple, set)):
                if not (set(actual) & set(expected)):
                    return False
            elif actual not in expected:
                return False
        return True

    @classmethod
    def _resolve_dim(cls, dim: str, context: EvaluationContext):
        if dim == 'process':
            return context.process_id
        return context.extra.get(dim)


class RuleEngine:
    """统一规则引擎（§4）。

    dispatch 流程：加载候选规则 → 优先级排序 → scope 过滤 → 熔断检查 → 条件求值 →
    动作执行 → 写执行日志 → 返回结果列表。

    Phase 0：不接入任何业务调用方；动作经全局 action_registry 派发（Phase 0 单测中
    自行注册测试执行器跑通 dispatch）。
    """

    # 优先级排序权重（P0 > P1 > P2）
    _PRIORITY_WEIGHT = {'P0': 0, 'P1': 1, 'P2': 2}

    def dispatch(self, context: EvaluationContext,
                 source_app: Optional[str] = None) -> List[ExecutionResult]:
        """根据上下文派发匹配的规则并执行动作。

        Args:
            context: 派发上下文。
            source_app: 可选家族过滤（如 'automation'）。委托派发时仅执行该家族的镜像
                规则，避免误伤其他家族；缺省 None 不过滤（Phase 0 单测兼容）。
        """
        rules = self._load_candidate_rules(context, source_app)
        results: List[ExecutionResult] = []

        for rule in rules:
            t0 = time.perf_counter()
            # ③ scope 过滤
            if not ScopeMatcher.matches(rule.scope_json, context):
                continue

            # ④ 熔断检查
            if self._is_circuit_open(rule):
                log = self._save_log(
                    rule, context,
                    evaluate_result=EvaluateResult.SKIPPED,
                    skip_reason='circuit_open',
                    execution_ms=self._elapsed_ms(t0),
                )
                results.append(ExecutionResult(rule_id=rule.id, matched=False, log_id=log.id))
                continue

            # ⑤ 条件求值
            try:
                matched, detail = ConditionEvaluator().evaluate(rule, context)
            except Exception as exc:  # 求值异常 → 记 ERROR 日志，跳过该规则
                log = self._save_log(
                    rule, context,
                    evaluate_result=EvaluateResult.ERROR,
                    error_message=str(exc),
                    execution_ms=self._elapsed_ms(t0),
                )
                results.append(ExecutionResult(rule_id=rule.id, matched=False, log_id=log.id))
                continue

            if not matched:
                log = self._save_log(
                    rule, context,
                    evaluate_result=EvaluateResult.UNMATCHED,
                    execution_ms=self._elapsed_ms(t0),
                )
                results.append(ExecutionResult(rule_id=rule.id, matched=False, log_id=log.id))
                continue

            # ⑥ 遍历 enabled 动作经 registry 执行
            action_results: List[ActionResult] = []
            action_types: List[str] = []
            for action in rule.ordered_actions:
                if not action.enabled:
                    continue
                result = action_registry.dispatch(context, action, rule)
                action_results.append(result)
                action_types.append(action.action_type)

            log = self._save_log(
                rule, context,
                evaluate_result=EvaluateResult.MATCHED,
                action_taken=';'.join(
                    f"{r.action_type}:{'ok' if r.success else 'fail'}" for r in action_results
                ) or 'matched',
                action_type=','.join(action_types),
                execution_ms=self._elapsed_ms(t0),
            )
            results.append(ExecutionResult(
                rule_id=rule.id, matched=True,
                action_results=action_results, log_id=log.id,
            ))

        return results

    # --- 内部辅助 ---

    def _load_candidate_rules(self, context: EvaluationContext,
                              source_app: Optional[str] = None) -> List[Rule]:
        """① 加载 trigger_type 匹配 / 启用 / 未软删 的规则；② 按优先级排序。"""
        qs = Rule.objects.filter(
            trigger_type=context.trigger_type,
            enabled=True,
            status=RuleStatus.ENABLED,
            deleted_at__isnull=True,
        )
        if source_app:
            qs = qs.filter(source_app=source_app)
        rules = list(qs)
        rules.sort(key=lambda r: (self._PRIORITY_WEIGHT.get(r.priority, 99), r.priority_rank))
        return rules

    def _is_circuit_open(self, rule: Rule) -> bool:
        """④ 熔断：聚合该规则历史日志失败率是否超过阈值。

        Phase 0 定义「失败」= evaluate_result == ERROR。无日志默认 False（不打开）。
        """
        logs = RuleExecutionLog.objects.filter(rule=rule)
        total = logs.count()
        if total == 0:
            return False
        failed = logs.filter(evaluate_result=EvaluateResult.ERROR).count()
        rate = failed / total
        return rate > rule.failure_rate_threshold

    def _save_log(self, rule: Rule, context: EvaluationContext, **kwargs) -> RuleExecutionLog:
        """⑦ 写入统一执行日志。"""
        return RuleExecutionLog.objects.create(
            rule=rule,
            rule_category=rule.category,
            trigger_type=context.trigger_type,
            candidate_id=context.candidate_id,
            application_id=context.application_id,
            stage_id=context.stage_id,
            link_id=context.link_id,
            process_id=context.process_id,
            **kwargs,
        )

    @staticmethod
    def _elapsed_ms(t0: float) -> int:
        return int((time.perf_counter() - t0) * 1000)
