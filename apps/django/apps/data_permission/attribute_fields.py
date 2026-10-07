"""数据权限「属性条件」字段源 —— 从指标目录（AtomicMetric）派生可配置标量字段。

设计要点（与实施计划 + 兵哥两条铁律对齐）：
  - 字段清单直接复用指标目录（AtomicMetric，按 source_path 前缀 entity. 筛选），
    保证「指标 -> 权限配置」的真实链路（权限暴露的字段就是指标定义）。
  - 但只暴露**能渲染下拉 / 数字步进器**的字段，杜绝自由文本手输：
      * 数值字段（IntegerField/FloatField/DecimalField 或 data_type=number）-> 数字步进器；
      * 枚举字段（模型有 choices，或 FSM state）-> 中文下拉；
      * 布尔字段 -> 是/否下拉；
      * 自由文本字符串（CharField/TextField 无 choices）-> 一律不暴露；
      * 日期字段 -> 一期不暴露。
  - 每个字段下发的运算符取自 UnifiedOperator 子集，并带中文标签（operators:[{value,label}]），
    前端直接渲染中文下拉，无需硬编码。
  - source_path 形如 entity.field 才纳（排除数组索引 / 嵌套 JSON 路径）。
"""
from __future__ import annotations

import importlib
import re

from django.core.exceptions import FieldDoesNotExist
from django.db.models import (
    BooleanField,
    DecimalField,
    FloatField,
    IntegerField,
)
from django_fsm import FSMField

# ---------- 实体 -> 模型类（懒加载，避免 import 环） ----------
_ENTITY_MODEL_PATHS: dict[str, str | None] = {
    'demand': 'apps.demand.models.Demand',
    'position': 'apps.position.models.Position',
    'candidate': 'apps.candidate.models.Candidate',
    'process': 'apps.process.models.RecruitmentProcess',
    'talent': None,
}

# FSM state 无 choices，用 curated 中文映射（与 models.TextChoices 保持一致）
_STATE_LABELS: dict[str, dict[str, str]] = {
    'demand': {
        'DRAFT': '草稿', 'PENDING': '待审批', 'REJECTED': '已驳回',
        'APPROVED': '已通过', 'RECRUITING': '招聘中', 'PAUSED': '已暂停',
        'COMPLETED': '已完成', 'CANCELLED': '已取消',
    },
    'position': {
        'DRAFT': '草稿', 'PENDING_PUBLISH': '待发布', 'PUBLISHED': '已发布',
        'RECRUITING': '招聘中', 'PAUSED': '已暂停', 'UNPUBLISHED': '已下架',
        'CLOSED': '已关闭',
    },
}

# UnifiedOperator -> 中文标签（与 rule_engine.models.UnifiedOperator 取值一致）
UNIFIED_OPERATOR_LABELS: dict[str, str] = {
    'EQ': '等于', 'NEQ': '不等于', 'GT': '大于', 'GTE': '大于等于',
    'LT': '小于', 'LTE': '小于等于', 'BETWEEN': '区间',
    'IN': '属于', 'NOT_IN': '不属于', 'IS_EMPTY': '为空',
    'IS_NOT_EMPTY': '不为空', 'CONTAINS': '包含', 'NOT_CONTAINS': '不包含',
    'REGEX_MATCH': '正则匹配',
}

# 各数据类型的可用运算符子集（兵哥铁律：运算符也全中文标签）
_OPERATOR_SETS: dict[str, list[str]] = {
    'number': ['EQ', 'NEQ', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN', 'IS_EMPTY'],
    'enum': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
    'boolean': ['EQ', 'NEQ'],
}


def operator_options(category: str) -> list[dict]:
    """返回某数据类型的运算符 [{value,label}]（中文标签）。"""
    return [
        {'value': op, 'label': UNIFIED_OPERATOR_LABELS[op]}
        for op in _OPERATOR_SETS.get(category, [])
    ]


_SIMPLE_PATH_RE = re.compile(r'^[a-z_]+$')


def _resolve_model(entity: str):
    """懒加载实体对应的 Django 模型类；无映射返回 None。"""
    path = _ENTITY_MODEL_PATHS.get(entity)
    if not path:
        return None
    module_path, cls = path.rsplit('.', 1)
    mod = importlib.import_module(module_path)
    return getattr(mod, cls)


def attribute_fields_for(entity: str) -> list[dict]:
    """返回某实体可作为「属性条件」配置的字段清单（已按兵哥铁律过滤为可下拉/数字字段）。

    结构：[{sourcePath, name(中文), dataType('number'|'enum'|'boolean'),
            enumValues:[{value,label}], operators:[{value,label}]}, ...]
    """
    from apps.metrics.models import AtomicMetric

    metrics = list(
        AtomicMetric.objects.filter(
            source_path__startswith=f'{entity}.', status='enabled'
        )
    )
    model = _resolve_model(entity)
    out: list[dict] = []

    for m in metrics:
        path = m.source_path
        tail = path.split('.', 1)[1] if '.' in path else path
        if not _SIMPLE_PATH_RE.match(tail):
            continue  # 排除数组索引 / 嵌套路径

        category: str | None = None
        enum_values: list[dict] = []

        if model is not None:
            try:
                f = model._meta.get_field(tail)
            except FieldDoesNotExist:
                # 指标 source_path 尾段与模型字段不匹配（动态字段/手填路径）→ 无类型信息
                f = None
            except Exception:  # noqa: BLE001 — _meta 内部异常不阻断字段目录构建, 降级为未知类型
                f = None

            if isinstance(f, (IntegerField, FloatField, DecimalField)):
                category = 'number'
            elif isinstance(f, BooleanField):
                category = 'boolean'
                enum_values = [
                    {'value': True, 'label': '是'},
                    {'value': False, 'label': '否'},
                ]
            elif isinstance(f, FSMField) and tail == 'state':
                category = 'enum'
                enum_values = [
                    {'value': k, 'label': v}
                    for k, v in _STATE_LABELS.get(entity, {}).items()
                ]
            elif getattr(f, 'choices', None):
                category = 'enum'
                enum_values = [
                    {'value': v, 'label': str(lbl)} for v, lbl in f.choices
                ]
            else:
                # 自由文本字符串 / 其它 -> 不暴露（避免用户手输）
                continue
        else:
            # 无模型可内省：仅按 data_type 放行 数值 / 布尔，其余跳过
            if m.data_type == 'number':
                category = 'number'
            elif m.data_type == 'boolean':
                category = 'boolean'
                enum_values = [
                    {'value': True, 'label': '是'},
                    {'value': False, 'label': '否'},
                ]
            else:
                continue

        out.append({
            'sourcePath': path,
            'name': m.name,
            'dataType': category,
            'enumValues': enum_values,
            'operators': operator_options(category),
        })

    return out
