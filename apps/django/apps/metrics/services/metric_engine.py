"""指标规则执行引擎（方案 A 增量 3）。

与 apps/rule_engine 的关系（**不新建第三套**）：
    - 运算符：复用 rule_engine.UnifiedOperator（11 种，含 BETWEEN/IN/IS_EMPTY）
    - 规则主体：可复用 rule_engine.Rule/Condition（execute_rule 适配），
      也支持不落库的一次性 execute(conditions, data)（避免 PRD T10「每次执行都
      createRule」产生垃圾规则数据）
    - 本引擎只负责 rule_engine 缺失的部分：按指标元数据取值（原子/派生）+ 分步结果

执行结果契约（对齐 PRD F-08）：
    {pass, logic, steps: [{index, pass, templateName, operator, operatorLabel,
                           actual, expected, detail, error}], summary}

异常处理（PRD F-09 非功能要求：任何异常都不许 500，降级为该步 FAIL）：
    模板不存在 / 运算符不被模板支持 / 字段解析失败 / 类型转换失败 / 其他异常
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from apps.rule_engine.models import UnifiedOperator

from .derived_registry import compute as derived_compute
from .field_resolver import (
    FieldResolveError,
    FieldResolverRegistry,
    TypeCastError,
    type_cast,
)

# 需要区间值的运算符
_RANGE_OPS = (UnifiedOperator.BETWEEN,)
# 需要集合值的运算符
_SET_OPS = (UnifiedOperator.IN, UnifiedOperator.NOT_IN)
# 不需要比较值的运算符
_VOID_OPS = (UnifiedOperator.IS_EMPTY, UnifiedOperator.IS_NOT_EMPTY)
# 字符串运算（包含 / 不包含 / 正则匹配）：期望值按原文处理，不参与数值/日期类型转换
_STRING_OPS = (
    UnifiedOperator.CONTAINS,
    UnifiedOperator.NOT_CONTAINS,
    UnifiedOperator.REGEX_MATCH,
)


def _is_empty(value: Any) -> bool:
    return value is None or value == '' or value == [] or value == {}


class MetricEngine:
    """指标规则执行引擎。全部为类方法，无状态。"""

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    @classmethod
    def execute(cls, conditions: List[dict], data: Dict[str, Any], logic: str = 'AND') -> dict:
        """执行一组条件（不落库）。conditions 元素：
        {templateId, operator, value, meta?{min,max}}
        """
        conditions = conditions or []
        steps = [cls._evaluate_condition(i, cond, data)
                 for i, cond in enumerate(conditions, start=1)]

        ok_flags = [bool(s['pass']) for s in steps]
        if logic == 'OR':
            overall = any(ok_flags)
        else:
            overall = all(ok_flags) and len(steps) > 0

        return {
            'pass': overall,
            'logic': logic,
            'steps': steps,
            'summary': cls._summary(overall, steps),
        }

    @classmethod
    def execute_rule(cls, rule, data: Dict[str, Any]) -> dict:
        """复用 rule_engine.Rule 执行（Condition.field 存模板 id）。"""
        conditions = []
        for cond in rule.ordered_conditions:
            conditions.append({
                'templateId': cond.field,
                'operator': cond.operator,
                'value': cond.value,
                'meta': cond.meta_json or {},
            })
        return cls.execute(conditions, data, logic=getattr(rule, 'condition_logic', 'ALL') == 'ANY' and 'OR' or 'AND')

    # ------------------------------------------------------------------
    # 单条条件
    # ------------------------------------------------------------------
    @classmethod
    def _evaluate_condition(cls, index: int, cond: dict, data: Dict[str, Any]) -> dict:
        from apps.metrics.models import MetricTemplate  # 局部导入，避免 app 加载期循环

        template_id = cond.get('templateId') or cond.get('template_id')
        operator = cond.get('operator')
        base = {
            'index': index,
            'pass': False,
            'templateName': '',
            'operator': operator,
            'operatorLabel': cls._op_label(operator),
            'actual': None,
            'expected': None,
            'detail': '',
            'error': '',
        }

        # 1) 模板存在性
        template = MetricTemplate.objects.filter(pk=template_id).select_related(
            'atomic_metric', 'derived_metric'
        ).first()
        if template is None:
            base['error'] = f'模板 {template_id} 不存在'
            base['detail'] = base['error']
            return base
        base['templateName'] = template.name

        # 2) 运算符合法性（PRD AC-04：后端必须拒绝模板不支持的运算符）
        allowed = template.operators or []
        if operator not in allowed:
            base['error'] = f'模板「{template.name}」不支持运算符「{cls._op_label(operator)}」'
            base['detail'] = base['error']
            return base

        metric = template.metric
        path = template.metric_path

        # 3) 取值（原子走路径解析，派生走计算函数注册表）
        try:
            actual_raw = cls._resolve_metric_value(template, metric, data)
        except FieldResolveError as exc:
            base['error'] = f'字段解析失败: {exc}'
            base['detail'] = base['error']
            return base
        except Exception as exc:  # noqa: BLE001 — 派生函数等未预期异常降级为 FAIL, 绝不 500 (指标计算层设计原则)
            base['error'] = f'取值异常: {exc}'
            base['detail'] = base['error']
            return base

        # 4) 类型转换
        try:
            actual = type_cast(actual_raw, template.data_type)
        except TypeCastError as exc:
            base['error'] = f'值 {actual_raw!r} 类型不合法: {exc}'
            base['detail'] = base['error']
            return base

        # 5) 期望值
        try:
            expected, expected_text = cls._expected(cond, template.data_type)
        except TypeCastError as exc:
            base['error'] = f'比较值不合法: {exc}'
            base['detail'] = base['error']
            return base

        # 6) 比较
        try:
            passed = cls._compare(operator, actual, expected, cond.get('meta') or {})
        except Exception as exc:  # noqa: BLE001 — 比较阶段异常降级为 FAIL (类型不匹配等), 规则继续被记录为未通过而非 500
            base['error'] = f'执行异常: {exc}'
            base['detail'] = base['error']
            return base

        unit = template.unit or ''
        base['pass'] = passed
        base['actual'] = cls._jsonable(actual)
        base['expected'] = expected_text
        base['detail'] = cls._detail(
            template.name, path, actual, operator, expected_text, unit
        )
        return base

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    @classmethod
    def _resolve_metric_value(cls, template, metric, data: Dict[str, Any]) -> Any:
        if template.metric_kind == 'derived':
            items = FieldResolverRegistry.resolve(metric.base_path, data)
            return derived_compute(metric.calc_func, items, metric.params or {}, data)
        return FieldResolverRegistry.resolve(metric.source_path, data)

    @classmethod
    def _expected(cls, cond: dict, data_type: str):
        """返回 (expected 对象, 展示文本)。"""
        op = cond.get('operator')
        if op in _VOID_OPS:
            return None, ''
        if op in _RANGE_OPS:
            meta = cond.get('meta') or {}
            low = type_cast(meta.get('min'), data_type)
            high = type_cast(meta.get('max'), data_type)
            return (low, high), f'[{cls._jsonable(low)}, {cls._jsonable(high)}]'
        if op in _SET_OPS:
            raw = cond.get('value')
            values = raw if isinstance(raw, list) else [raw]
            casted = [type_cast(v, data_type) for v in values]
            return casted, '、'.join(str(cls._jsonable(v)) for v in casted)
        if op in _STRING_OPS:
            # 字符串运算：期望值作为原文（子串 / 正则），不做数值或日期类型转换
            raw = cond.get('value')
            text = '' if raw is None else (raw if isinstance(raw, str) else str(raw))
            if op == UnifiedOperator.REGEX_MATCH:
                # 提前校验正则合法性，避免比较阶段才抛错（仍降级为 FAIL，绝不 500）
                try:
                    re.compile(text)
                except re.error:
                    raise TypeCastError(f'正则表达式不合法: {text}')
            return text, text
        expected = type_cast(cond.get('value'), data_type)
        return expected, cls._jsonable(expected)

    @classmethod
    def _compare(cls, operator: str, actual: Any, expected: Any, meta: dict) -> bool:
        if operator == UnifiedOperator.IS_EMPTY:
            return _is_empty(actual)
        if operator == UnifiedOperator.IS_NOT_EMPTY:
            return not _is_empty(actual)
        if operator == UnifiedOperator.BETWEEN:
            # 期望值已由 _expected 按 data_type 转换并打包为 (min, max)
            if not (isinstance(expected, tuple) and len(expected) == 2):
                raise ValueError('区间运算符缺少 min/max')
            low, high = expected
            if actual is None or low is None or high is None:
                return False
            return low <= actual <= high
        if operator == UnifiedOperator.IN:
            return actual in (expected or [])
        if operator == UnifiedOperator.NOT_IN:
            return actual not in (expected or [])
        if operator == UnifiedOperator.CONTAINS:
            if actual is None or expected is None:
                return False
            return str(actual).find(str(expected)) >= 0
        if operator == UnifiedOperator.NOT_CONTAINS:
            if actual is None or expected is None:
                return False
            return str(actual).find(str(expected)) < 0
        if operator == UnifiedOperator.REGEX_MATCH:
            if actual is None or expected is None:
                return False
            try:
                return re.search(str(expected), str(actual)) is not None
            except re.error:
                raise ValueError(f'正则表达式不合法: {expected}')
        if actual is None or expected is None:
            return False
        if operator == UnifiedOperator.EQ:
            return actual == expected
        if operator == UnifiedOperator.NEQ:
            return actual != expected
        if operator == UnifiedOperator.GT:
            return actual > expected
        if operator == UnifiedOperator.GTE:
            return actual >= expected
        if operator == UnifiedOperator.LT:
            return actual < expected
        if operator == UnifiedOperator.LTE:
            return actual <= expected
        raise ValueError(f'未实现的运算符: {operator}')

    @staticmethod
    def _op_label(operator: Optional[str]) -> str:
        try:
            return UnifiedOperator(operator).label
        except Exception:  # noqa: BLE001 — 未知运算符返原值 (容错, label 仅用于展示, 不阻断比较逻辑)
            return str(operator or '')

    @staticmethod
    def _detail(name: str, path: str, actual: Any, operator: str, expected_text: str, unit: str) -> str:
        """生成人话描述，如：年龄(candidate.age) = 32 岁 大于 30 岁"""
        op_text = MetricEngine._op_label(operator)
        actual_text = f'{MetricEngine._jsonable(actual)}{unit}'.strip()
        if operator in _VOID_OPS:
            return f'{name}({path}) = {actual_text} {op_text}'.strip()
        return f'{name}({path}) = {actual_text} {op_text} {expected_text}{unit}'.strip()

    @staticmethod
    def _summary(overall: bool, steps: List[dict]) -> str:
        total = len(steps)
        failed = [s for s in steps if not s['pass']]
        if total == 0:
            return '没有配置任何条件'
        if overall:
            return f'{total} 个条件全部满足，规则通过'
        first = failed[0] if failed else None
        if first and first.get('error'):
            return f'第 {first["index"]} 个条件无法判定：{first["error"]}'
        return f'{total} 个条件中有 {len(failed)} 个未满足，规则不通过'

    @staticmethod
    def _jsonable(value: Any) -> Any:
        """把 date/datetime 转为字符串，保证可 JSON 序列化。"""
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        if isinstance(value, (list, tuple)):
            return [MetricEngine._jsonable(v) for v in value]
        return value
