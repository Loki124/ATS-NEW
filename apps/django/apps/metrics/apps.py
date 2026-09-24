from django.apps import AppConfig


class MetricsConfig(AppConfig):
    name = 'apps.metrics'
    verbose_name = '指标库（规则引擎指标层）'

    def ready(self):
        """导入即注册内置派生计算函数（幂等），保证执行引擎派发前函数已就位。

        新增计算函数只需在 services/derived_registry.py 内 @register 一个新函数，
        无需改动本文件与执行引擎（开闭原则）。
        """
        from .services import derived_registry  # noqa: F401
