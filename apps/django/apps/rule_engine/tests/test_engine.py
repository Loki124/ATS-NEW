"""RuleEngine 主路径与边界单测（Phase 0）。

覆盖：主路径匹配 + 写日志 + 执行器被调用；scope 不命中 / 条件不命中 / 软删 / disabled
被跳过不执行；熔断（circuit-breaker）场景被 SKIPPED。

Phase 0：动作经全局 action_registry 派发；本模块注册一个测试用执行器跑通 dispatch。
"""
import pytest

from apps.rule_engine.models import (
    Action,
    Condition,
    EvaluateResult,
    Rule,
    RuleCategory,
    RuleExecutionLog,
    RuleStatus,
    UnifiedActionType,
    UnifiedOperator,
    UnifiedTriggerType,
)
from apps.rule_engine.services import (
    ActionExecutor,
    ActionResult,
    EvaluationContext,
    RuleEngine,
    action_registry,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# 测试用动作执行器（Phase 0 仅骨架，自行注册跑通 dispatch）
# ---------------------------------------------------------------------------

CALLS = []


class _TestExecutor(ActionExecutor):
    def supports(self, action_type):
        return True  # 测试用：支持所有类型

    def execute(self, context, action, rule):
        CALLS.append((rule.id, action.action_type))
        return ActionResult(success=True, action_type=action.action_type, message='test-ok')


# 注册到引擎级全局注册表（Phase 0 仅此一个）
action_registry.register(_TestExecutor())


@pytest.fixture(autouse=True)
def _reset_calls():
    # T10 (2026-09-03 fix): Phase 2+ 生产 executor（AutoAdvance / AllowExecutor / ...）
    # 在 apps.ready() 里注册到 action_registry，模块级 _TestExecutor() 注册被追加到末尾。
    # dispatch 按注册顺序找第一个 supports=True 的 executor 执行 → _TestExecutor 永远轮不到，
    # CALLS 一直是 []。
    # 修法：每个 test setUp 把 _TestExecutor 实例移到 _executors[0]，让 production executor
    # 落到后面。teardown 时若 _TestExecutor 不在头部再移回去（兼容外部 test 顺序）。
    executors = action_registry._executors
    test_executor_indices = [i for i, e in enumerate(executors) if isinstance(e, _TestExecutor)]
    moved_from = None
    if test_executor_indices:
        i = test_executor_indices[0]
        if i != 0:
            moved_from = executors.pop(i)
            executors.insert(0, moved_from)
    else:
        # 未注册（个别场景 conftest 清理过），补注册到头部
        action_registry.register(_TestExecutor())
        executors.insert(0, executors.pop(-1))
    CALLS.clear()
    yield
    CALLS.clear()
    # teardown: 还原位置（若之前是头部就不要动）
    if moved_from is not None and executors and isinstance(executors[0], _TestExecutor):
        e = executors.pop(0)
        # 放到原索引（若原索引已变则放末尾）
        target = i if i < len(executors) else len(executors)
        executors.insert(target, e)


# ---------------------------------------------------------------------------
# 构造辅助
# ---------------------------------------------------------------------------

def _make_rule(**over):
    """构造一条启用、ENABLED、STAGE_ENTERED 的规则，带 2 条件 + 1 动作。"""
    rule = Rule.objects.create(
        name=over.pop('name', 'engine-rule'),
        category=over.pop('category', RuleCategory.TCA),
        trigger_type=over.pop('trigger_type', UnifiedTriggerType.STAGE_ENTERED),
        scope_json=over.pop('scope_json', {}),
        condition_expression=over.pop('condition_expression', '(1 AND 2)'),
        condition_logic=over.pop('condition_logic', 'ALL'),
        enabled=over.pop('enabled', True),
        status=over.pop('status', RuleStatus.ENABLED),
        **over,
    )
    Condition.objects.create(rule=rule, seq=1, field='age', operator=UnifiedOperator.GT, value=18)
    Condition.objects.create(rule=rule, seq=2, field='level', operator=UnifiedOperator.EQ, value='P1')
    Action.objects.create(rule=rule, seq=1, action_type=UnifiedActionType.ALLOW, enabled=True)
    return rule


def _ctx(extra=None, **kw):
    return EvaluationContext(
        trigger_type=UnifiedTriggerType.STAGE_ENTERED,
        extra=extra or {},
        **kw,
    )


# ---------------------------------------------------------------------------
# 主路径
# ---------------------------------------------------------------------------

def test_dispatch_main_path_matches_and_executes():
    rule = _make_rule(scope_json={'bu': 'tech'})
    ctx = _ctx({'bu': 'tech', 'age': 20, 'level': 'P1'})

    results = RuleEngine().dispatch(ctx)

    assert len(results) == 1
    r = results[0]
    assert r.rule_id == rule.id
    assert r.matched is True
    # 执行器被调用
    assert CALLS == [(rule.id, UnifiedActionType.ALLOW)]
    # 写了日志
    assert r.log_id is not None
    log = RuleExecutionLog.objects.get(pk=r.log_id)
    assert log.evaluate_result == EvaluateResult.MATCHED
    assert log.rule_category == RuleCategory.TCA


# ---------------------------------------------------------------------------
# 边界：被跳过 / 不执行
# ---------------------------------------------------------------------------

def test_scope_miss_skipped():
    rule = _make_rule(scope_json={'bu': 'tech'})
    ctx = _ctx({'bu': 'other', 'age': 20, 'level': 'P1'})  # scope 不命中
    results = RuleEngine().dispatch(ctx)
    assert results == []  # 直接被 scope 过滤，不进入匹配
    assert CALLS == []  # 执行器未调用


def test_condition_miss_unmatched():
    rule = _make_rule(scope_json={'bu': 'tech'})
    ctx = _ctx({'bu': 'tech', 'age': 20, 'level': 'X'})  # 条件2 不满足
    results = RuleEngine().dispatch(ctx)
    assert len(results) == 1
    assert results[0].matched is False
    assert CALLS == []  # 未命中 → 不执行
    log = RuleExecutionLog.objects.get(pk=results[0].log_id)
    assert log.evaluate_result == EvaluateResult.UNMATCHED


def test_soft_deleted_rule_excluded():
    rule = _make_rule(scope_json={'bu': 'tech'})
    rule.soft_delete()  # 软删
    ctx = _ctx({'bu': 'tech', 'age': 20, 'level': 'P1'})
    results = RuleEngine().dispatch(ctx)
    assert results == []  # 软删规则不加载
    assert CALLS == []


def test_disabled_rule_excluded():
    rule = _make_rule(scope_json={'bu': 'tech'}, enabled=False)
    ctx = _ctx({'bu': 'tech', 'age': 20, 'level': 'P1'})
    results = RuleEngine().dispatch(ctx)
    assert results == []  # disabled 规则不加载
    assert CALLS == []


# ---------------------------------------------------------------------------
# 熔断
# ---------------------------------------------------------------------------

def test_circuit_breaker_skips():
    rule = _make_rule(scope_json={'bu': 'tech'})
    # 预置高失败率日志：3 条 ERROR
    for _ in range(3):
        RuleExecutionLog.objects.create(
            rule=rule,
            rule_category=rule.category,
            trigger_type=rule.trigger_type,
            evaluate_result=EvaluateResult.ERROR,
        )
    assert RuleEngine()._is_circuit_open(rule) is True

    ctx = _ctx({'bu': 'tech', 'age': 20, 'level': 'P1'})
    results = RuleEngine().dispatch(ctx)
    assert len(results) == 1
    assert results[0].matched is False
    assert CALLS == []  # 熔断 → 不执行
    log = RuleExecutionLog.objects.get(pk=results[0].log_id)
    assert log.evaluate_result == EvaluateResult.SKIPPED
    assert log.skip_reason == 'circuit_open'


def test_low_failure_rate_not_open():
    rule = _make_rule(scope_json={'bu': 'tech'})
    # 1 ERROR / 1 MATCHED → 率 0.5，未超过默认阈值 0.5 → 不打开
    RuleExecutionLog.objects.create(
        rule=rule, rule_category=rule.category,
        trigger_type=rule.trigger_type, evaluate_result=EvaluateResult.ERROR,
    )
    RuleExecutionLog.objects.create(
        rule=rule, rule_category=rule.category,
        trigger_type=rule.trigger_type, evaluate_result=EvaluateResult.MATCHED,
    )
    assert RuleEngine()._is_circuit_open(rule) is False
