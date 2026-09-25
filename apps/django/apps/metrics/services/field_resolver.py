"""字段解析器 —— 点路径取值 + 类型转换（方案 A 增量 1）。

补齐 apps/rule_engine/services.py:_resolve_value 的能力缺口：
    现状：仅 flat key（getattr(context, field) / context.extra.get(field)）
    本模块：支持 a.b.c 点路径 + 数组数字下标（candidate.workExperience.0.company）

可扩展性：FieldResolverRegistry 按 source_type 路由；新增一种取值方式（如 SQL_COLUMN）
只需实现 resolve 接口并 register，不改本文件与执行引擎（开闭原则）。

安全：路径段拒绝 '__' 前缀，杜绝 __class__ / __proto__ 之类的路径穿越与属性逃逸。
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from apps.metrics.models import MetricDataType

_MISSING = object()


class FieldResolveError(Exception):
    """字段解析失败。消息直接呈现给配置人员，故必须是人话。"""


class TypeCastError(Exception):
    """值类型转换失败。"""


def _parse_date(value: Any) -> date:
    """把值解析为 date。支持 date / datetime / ISO 字符串。"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise TypeCastError('空字符串不是合法日期')
        # 兼容带时间的 ISO 串（取日期部分）
        text = text.replace('T', ' ').split(' ')[0]
        try:
            return date.fromisoformat(text)
        except ValueError:
            raise TypeCastError(f'"{value}" 不是合法日期（应为 YYYY-MM-DD）')
    raise TypeCastError(f'{value!r} 不是合法日期')


def type_cast(value: Any, data_type: str):
    """按指标数据类型转换值。失败抛 TypeCastError（由引擎转为该步 FAIL）。

    空/None 原样返回 —— 交由「为空/不为空」运算符判定，不应在此误抛。
    """
    if value is None or value == '':
        return value

    if data_type == MetricDataType.NUMBER:
        # T5（INV-9）：一律返回 Decimal，杜绝 float 二进制精度陷阱。
        # 入参可能是 int / float / str（前端按 T5 约定传字符串），统一 Decimal(str)。
        if isinstance(value, bool):
            raise TypeCastError(f'{value!r} 不是合法数值')
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            # 先转 str 再 Decimal，避免 float 二进制尾差直接带入 Decimal
            text = str(value)
        else:
            text = str(value).strip()
        if text == '':
            raise TypeCastError('空字符串不是合法数值')
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError, TypeError):
            raise TypeCastError(f'{value!r} 不是合法数值')

    if data_type == MetricDataType.BOOLEAN:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ('true', '1', 'yes', 'y', '是'):
            return True
        if text in ('false', '0', 'no', 'n', '否'):
            return False
        raise TypeCastError(f'{value!r} 不是合法布尔值')

    if data_type == MetricDataType.DATE:
        return _parse_date(value)

    return str(value)


class ObjectPathResolver:
    """对象路径解析器：dot 路径 + 数组下标。"""

    def resolve(self, source_path: str, data: Dict[str, Any]) -> Any:
        if not source_path or not isinstance(source_path, str):
            raise FieldResolveError('字段路径为空')
        if '.' not in source_path:
            raise FieldResolveError(
                f'字段路径 "{source_path}" 必须包含 "." （如 candidate.age）'
            )
        if not isinstance(data, dict):
            raise FieldResolveError('数据根节点必须是 dict')

        current: Any = data
        walked: list[str] = []
        for part in source_path.split('.'):
            current = self._step(current, part, source_path, walked)
            walked.append(part)
        return current

    @staticmethod
    def _step(current: Any, part: str, source_path: str, walked: list[str]) -> Any:
        # 路径穿越防护：拒绝 dunder 段（__class__ / __proto__ / __globals__ 等）
        if part.startswith('__') or part == '':
            raise FieldResolveError(f'字段路径 "{source_path}" 含非法段 "{part}"')

        if isinstance(current, dict):
            if part not in current:
                raise FieldResolveError(
                    f'字段解析失败: {".".join(walked + [part]) if walked else part} 不存在'
                )
            return current[part]

        if isinstance(current, (list, tuple)):
            try:
                index = int(part)
            except (TypeError, ValueError):
                raise FieldResolveError(
                    f'字段路径 "{source_path}" 的 "{part}" 不是合法数组下标'
                )
            try:
                return current[index]
            except IndexError:
                raise FieldResolveError(
                    f'字段解析失败: 下标 {index} 超出范围（共 {len(current)} 项）'
                )

        raise FieldResolveError(
            f'字段路径 "{source_path}" 无法在 {type(current).__name__} 上取 "{part}"'
        )


class FieldResolverRegistry:
    """解析器注册表（开闭原则）。默认只有 OBJECT_PATH。"""

    _resolvers: Dict[str, Any] = {'OBJECT_PATH': ObjectPathResolver()}

    @classmethod
    def register(cls, source_type: str, resolver: Any) -> None:
        cls._resolvers[source_type] = resolver

    @classmethod
    def resolve(cls, source_path: str, data: Dict[str, Any], source_type: str = 'OBJECT_PATH') -> Any:
        resolver = cls._resolvers.get(source_type or 'OBJECT_PATH')
        if resolver is None:
            raise FieldResolveError(f'未注册的取值方式: {source_type}')
        return resolver.resolve(source_path, data)
