"""skip / archive 规则消费方派发器（METRIC 作为条件源的最终求值入口）。

⚠️ 这不是「第三套规则引擎」——它只是 skip/archive 触发链路的**条件求值派发器**：
    - METRIC 条件项：直接委托 apps.metrics.services.metric_engine.MetricEngine
      （统一指标条件求值器 evaluate_metric_condition），零重复实现取值 / 比较 / 解析。
    - legacy 条件项（CANDIDATE / DEMAND / POSITION）：复用既有三类快照
      （build_candidate_snapshot / build_demand_snapshot / build_position_snapshot）
      + FieldResolverRegistry 做点路径解析，与指标层完全一致，不另起炉灶。
    - STAGE_STATUS：skip/archive 通常不引用阶段状态，留作「不求值」并明确说明。

运算符词表、取值层、比较逻辑全部复用既有组件（UnifiedOperator / MetricEngine._compare /
FieldResolverRegistry / type_cast），本模块只负责「按 condition_type 路由到正确求值器并统一
返回同形契约」，保证前端 / skip-archive 调用方拿到结构一致的结果。

结果契约（与 MetricEngine.evaluate_metric_condition 同形）：
    {pass, template_id, template_name, operator, operator_label,
     actual, expected, detail, error, degraded}

任何异常均降级为 {pass:False, degraded:True}（fail-safe，绝不 500）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from apps.metrics.services.candidate_snapshot import (
    build_candidate_snapshot,
    build_demand_snapshot,
    build_position_snapshot,
)
from apps.metrics.services.field_resolver import (
    FieldResolveError,
    FieldResolverRegistry,
    TypeCastError,
    type_cast,
)
from apps.metrics.services.metric_engine import MetricEngine

logger = logging.getLogger(__name__)

# skip/archive 支持的 legacy 条件类型
_LEGACY_TYPES = ('CANDIDATE', 'DEMAND', 'POSITION')

# 集合类 / 区间类运算符（对齐 MetricEngine._expected 语义，避免 blanket type_cast 误判）
_RANGE_OPS = ('BETWEEN',)
_SET_OPS = ('IN', 'NOT_IN')


class RuleItemEvaluator:
    """单条条件项求值 + 整条规则表达式求值（skip/archive 消费方）。

    context 须含 'candidate_id'，可选 'demand_id' / 'position_id'。
    """

    # ------------------------------------------------------------------
    # 单条条件项求值
    # ------------------------------------------------------------------
    @classmethod
    def evaluate_item(cls, item: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """对单条条件项求值，返回与 MetricEngine 同形的结果契约。

        item 键：condition_type / field / operator / value / meta（meta 可选）。
        """
        try:
            condition_type = item.get('condition_type')
            operator = item.get('operator')

            # METRIC：直接委托统一求值器（其已含完整契约，含 pass）
            if condition_type == 'METRIC':
                return MetricEngine.evaluate_metric_condition(
                    item['field'], context, operator, item.get('value'), item.get('meta'),
                )

            # STAGE_STATUS：skip/archive 暂不引用阶段状态，留作不求值
            if condition_type == 'STAGE_STATUS':
                return {
                    'pass': False,
                    'template_id': item.get('field') or '',
                    'template_name': item.get('field') or '',
                    'operator': operator,
                    'operator_label': MetricEngine._op_label(operator),
                    'actual': None,
                    'expected': None,
                    'detail': '',
                    'error': 'STAGE_STATUS 在 skip/archive 中暂不支持',
                    'degraded': False,
                }

            # legacy CANDIDATE / DEMAND / POSITION：复用三类快照 + FieldResolverRegistry
            if condition_type in _LEGACY_TYPES:
                return cls._evaluate_legacy_item(item, context)

            # 未知 condition_type：不阻断，降级为未命中
            logger.warning('RuleItemEvaluator 未知 condition_type=%s', condition_type)
            return {
                'pass': False,
                'template_id': item.get('field') or '',
                'template_name': item.get('field') or '',
                'operator': operator,
                'operator_label': MetricEngine._op_label(operator),
                'actual': None,
                'expected': None,
                'detail': '',
                'error': f'不支持的条件类型: {condition_type}',
                'degraded': False,
            }
        except Exception as exc:  # noqa: BLE001 — fail-safe: 任何异常降级为未命中, 绝不 500
            logger.warning('RuleItemEvaluator.evaluate_item 异常降级: %s', exc)
            return {
                'pass': False,
                'template_id': (item or {}).get('field') or '',
                'template_name': (item or {}).get('field') or '',
                'operator': (item or {}).get('operator'),
                'operator_label': MetricEngine._op_label((item or {}).get('operator')),
                'actual': None,
                'expected': None,
                'detail': '',
                'error': str(exc),
                'degraded': True,
            }

    @classmethod
    def _evaluate_legacy_item(cls, item: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """legacy 条件项：三类快照 + FieldResolverRegistry 点路径解析（不依赖 ORM Evaluator）。"""
        operator = item.get('operator')
        field = item.get('field')
        ctx = context or {}

        # 1) 合并三类快照（缺哪个就只缺一源，不影响其它源解析）
        data: Dict[str, Any] = {}
        cid = ctx.get('candidate_id')
        did = ctx.get('demand_id')
        pid = ctx.get('position_id')
        if cid:
            try:
                data.update(build_candidate_snapshot(cid))
            except Exception:  # noqa: BLE001 — 快照组装失败跳过
                pass
        if did:
            try:
                data.update(build_demand_snapshot(did))
            except Exception:  # noqa: BLE001
                pass
        if pid:
            try:
                data.update(build_position_snapshot(pid))
            except Exception:  # noqa: BLE001
                pass

        # 2) 点路径解析（与指标层共享 FieldResolverRegistry）
        actual: Any = None
        try:
            actual = FieldResolverRegistry.resolve(field, data)
        except (FieldResolveError, Exception) as exc:  # noqa: BLE001 — 路径缺失/解析失败 → 视为无值
            logger.warning('RuleItemEvaluator legacy 解析失败 field=%s err=%s', field, exc)

        # 3) data_type：优先取 source_path 命中的 AtomicMetric，缺则默认 string
        data_type = 'string'
        try:
            from apps.metrics.models import AtomicMetric
            metric = AtomicMetric.objects.filter(
                source_path=field, status='enabled', deleted_at__isnull=True,
            ).first()
            if metric is not None:
                data_type = metric.data_type
        except Exception:  # noqa: BLE001 — data_type 查询失败退化为 string
            pass

        # 4) 类型转换 + 比较（复用 MetricEngine._compare）
        # actual 始终按 data_type 转换（失败兜底原值）
        try:
            actual_cast = type_cast(actual, data_type)
        except TypeCastError:
            actual_cast = actual

        value = item.get('value')
        # 期望值按运算符分派（对齐 MetricEngine._expected 语义）：
        #  - BETWEEN：期望值为 (min, max) 元组，满足 MetricEngine._compare 的 2 元素元组要求
        #  - IN / NOT_IN：期望值为逐元素按 data_type 转换的列表
        #  - 其余（标量 / 字符串类 CONTAINS 等）：期望值整体按 data_type 转换
        # 任一元素 cast 失败兜底保留原值（绝不因单值脏数据静默误判）。
        if operator in _RANGE_OPS and isinstance(value, (list, tuple)) and len(value) == 2:
            try:
                expected_cast = (
                    type_cast(value[0], data_type),
                    type_cast(value[1], data_type),
                )
            except TypeCastError:
                expected_cast = tuple(value)
        elif operator in _SET_OPS and isinstance(value, list):
            try:
                expected_cast = [type_cast(v, data_type) for v in value]
            except TypeCastError:
                expected_cast = value
        else:
            try:
                expected_cast = type_cast(value, data_type)
            except TypeCastError:
                expected_cast = value

        passed = MetricEngine._compare(operator, actual_cast, expected_cast, item.get('meta') or {})

        return {
            'pass': passed,
            'template_id': field or '',
            'template_name': field or '',
            'operator': operator,
            'operator_label': MetricEngine._op_label(operator),
            'actual': MetricEngine._jsonable(actual_cast),
            'expected': MetricEngine._jsonable(expected_cast),
            'detail': '',
            'error': '',
            'degraded': False,
        }

    # ------------------------------------------------------------------
    # 整条规则表达式求值
    # ------------------------------------------------------------------
    @classmethod
    def evaluate_rule(cls, rule_json: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """对整条规则（items + expression）求值，返回最终布尔结果。

        rule_json: {items: [item dict, ...], expression: '(1 AND 2) OR 3'}
        expression 为空/空白 → 视为全部条件 AND。
        """
        try:
            from apps.process.expressions import evaluate

            items = rule_json.get('items') or []
            expression = (rule_json.get('expression') or '').strip()

            condition_results: Dict[int, bool] = {}
            for idx, item in enumerate(items):
                seq = item.get('item_seq', idx + 1)
                try:
                    result = cls.evaluate_item(item, context)
                    condition_results[seq] = bool(result.get('pass', False))
                except Exception as exc:  # noqa: BLE001 — 单条异常不影响整条规则判定
                    logger.warning('RuleItemEvaluator 单条求值异常 seq=%s err=%s', seq, exc)
                    condition_results[seq] = False

            # 表达式为空 → 视为全部 AND
            if not expression:
                return all(condition_results.values()) if condition_results else False

            return bool(evaluate(expression, condition_results))
        except Exception as exc:  # noqa: BLE001 — 表达式解析异常 → 整条规则判不通过, 不阻断主流程
            logger.warning('RuleItemEvaluator.evaluate_rule 异常降级: %s', exc)
            return False
