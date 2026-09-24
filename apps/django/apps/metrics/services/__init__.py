"""指标库 services 包（规则引擎指标层）。

三个模块职责：
    field_resolver   —— 点路径取值 + 类型转换（补齐 rule_engine 的 flat key 缺口）
    derived_registry —— 派生指标计算函数注册表（遍历/聚合/时间窗）
    metric_engine    —— 执行引擎（复用 rule_engine.UnifiedOperator 做比较）

注意：derived_registry 的注册发生在 import 时（装饰器），apps.MetricsConfig.ready()
会显式导入它以保证执行前函数已就位。
"""
