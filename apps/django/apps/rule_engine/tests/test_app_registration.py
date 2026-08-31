"""验证 rule_engine app 正确注册到 Django（mirror add_candidate 写法）。

Phase 0：仅断言 app 在 INSTALLED_APPS、四个模型可 import，不触碰任何现有 app。
"""
from django.apps import apps


def test_rule_engine_app_is_registered():
    """app 必须在 INSTALLED_APPS 中，且 name / verbose_name 正确。"""
    config = apps.get_app_config('rule_engine')
    assert config.name == 'apps.rule_engine'
    assert config.verbose_name == '统一规则引擎'


def test_four_models_importable():
    """四个核心模型必须可 import（建模成功的基本前提）。"""
    from apps.rule_engine.models import (
        Action,
        Condition,
        Rule,
        RuleExecutionLog,
    )
    for model in (Rule, Condition, Action, RuleExecutionLog):
        assert model is not None
