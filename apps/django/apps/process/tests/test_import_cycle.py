"""#20 / #21 回归：同会话内交叉加载 candidate↔application 与 process↔metrics 不抛 ImportError。

审计 CODE_REVIEW_2026-10-08 §2.2 将这两处列为 P0 循环依赖（A1 / A2）。
修复为纯导入时机搬运（模块级 → 方法内 / 字符串 FK），不改变运行时行为。
本测试作为守卫，确保任一侧改为模块级反向引用时立即失败。
"""
import importlib
import inspect

import pytest


# 同会话内按“最坏顺序”加载双方，触发潜在循环依赖。
_CANDIDATE_APP_MODULES = [
    'apps.candidate.models',
    'apps.candidate.serializers',
    'apps.application.models',
    'apps.application.serializers',
]
_PROCESS_METRICS_MODULES = [
    'apps.process.services.rule_item_evaluator',
    'apps.metrics.services.template_impact',
]


def test_no_circular_import_candidate_application():
    for mod in _CANDIDATE_APP_MODULES:
        assert importlib.import_module(mod) is not None


def test_no_circular_import_process_metrics():
    for mod in _PROCESS_METRICS_MODULES:
        assert importlib.import_module(mod) is not None


def test_application_models_no_module_level_candidate_import():
    # #20: application/models.py 顶层不得再模块级 import apps.candidate.models (改为字符串 FK)
    from apps.application import models as m

    src = inspect.getsource(m)
    top = src.split('class Application', 1)[0]
    assert 'from apps.candidate.models import' not in top, (
        'application/models.py 顶层仍模块级导入 Candidate, 循环依赖边未切断'
    )


def test_rule_item_evaluator_no_module_level_metrics_import():
    # #21: rule_item_evaluator 顶层不得再模块级 import apps.metrics.* (改为方法内惰性)
    from apps.process.services import rule_item_evaluator as m

    src = inspect.getsource(m)
    top = src.split('logger = logging.getLogger(__name__)', 1)[0]
    assert 'from apps.metrics' not in top, (
        'rule_item_evaluator 顶层仍模块级导入 metrics, 循环依赖边未切断'
    )
