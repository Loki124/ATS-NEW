from django.apps import AppConfig


class RuleEngineConfig(AppConfig):
    name = 'apps.rule_engine'
    verbose_name = '统一规则引擎'

    def ready(self):
        # 注册各 family 的动作执行器到全局 action_registry（幂等，import 即注册）。
        # 确保统一引擎派发前执行器已就位，不依赖各业务 app 的委托代码是否先被加载。
        from .integrations import (  # noqa: F401
            automation_executors,
            campus_control_executors,
            entry_condition_executors,
            mou_executors,
            time_limit_executors,
        )
