"""指标字段类型 → 支持的运算符能力白名单（指标定义视图的核心元数据）。

设计目标（用户诉求）：
    依据字段类型（字符串 / 数值 / 日期 / 布尔 / 枚举等）尽可能详尽地输出所支持的运算符。
    白名单内的运算符**必须是引擎真实实现**的（rule_engine.UnifiedOperator + metric_engine
    已支持的 14 种），绝不罗列引擎跑不动的占位运算符 —— 契合「目标是真实可靠」原则。

字段类型来源有两处：
    1) 指标自身 data_type（MetricDataType：number / string / boolean / date）
    2) 动态字段 field_type（DynamicField.FieldType，类型更细，含 SELECT 等枚举类）

对外提供：
    operators_for(data_type, is_enum=False) -> [op_value...]   取数白名单
    operator_label(op_value) -> 中文标签
    field_type_capability(field_type) -> 映射 + 白名单（供自动生成指标用）
"""
from typing import Dict, List

from apps.rule_engine.models import UnifiedOperator as OP

# ---------------------------------------------------------------------------
# 能力矩阵：指标数据类型 → 支持的运算符
# ---------------------------------------------------------------------------
_MATRIX: Dict[str, List[str]] = {
    # 数值：全量比较 + 区间 + 集合 + 空值，最丰富
    'number': [
        OP.EQ, OP.NEQ,
        OP.GT, OP.GTE, OP.LT, OP.LTE,
        OP.BETWEEN,
        OP.IN, OP.NOT_IN,
        OP.IS_EMPTY, OP.IS_NOT_EMPTY,
    ],
    # 字符串：等值 + 集合 + 包含/正则 + 空值
    'string': [
        OP.EQ, OP.NEQ,
        OP.IN, OP.NOT_IN,
        OP.CONTAINS, OP.NOT_CONTAINS, OP.REGEX_MATCH,
        OP.IS_EMPTY, OP.IS_NOT_EMPTY,
    ],
    # 日期：等值 + 比较 + 区间 + 空值（不含集合/包含，语义不通）
    'date': [
        OP.EQ, OP.NEQ,
        OP.GT, OP.GTE, OP.LT, OP.LTE,
        OP.BETWEEN,
        OP.IS_EMPTY, OP.IS_NOT_EMPTY,
    ],
    # 布尔：仅等值 + 空值
    'boolean': [
        OP.EQ, OP.NEQ,
        OP.IS_EMPTY, OP.IS_NOT_EMPTY,
    ],
    # 枚举（单选 / 多选 / 列表）：等值 + 集合 + 空值
    'enum': [
        OP.EQ, OP.NEQ,
        OP.IN, OP.NOT_IN,
        OP.IS_EMPTY, OP.IS_NOT_EMPTY,
    ],
}

# 运算符中文标签（与 rule_engine 枚举标签一致，避免两处维护）
_LABELS: Dict[str, str] = {op: OP(op).label for op in OP.values}


def operators_for(data_type: str, is_enum: bool = False) -> List[str]:
    """返回某指标类型支持的运算符取值列表（顺序即矩阵定义顺序）。"""
    key = 'enum' if is_enum else (data_type or 'string')
    return list(_MATRIX.get(key, _MATRIX['string']))


def operator_label(op_value: str) -> str:
    """运算符取值 → 中文标签（未知返回原值）。"""
    return _LABELS.get(op_value, op_value or '')


# ---------------------------------------------------------------------------
# 动态字段类型 → 指标类型映射（供「新增字段自动生成指标定义」使用）
# ---------------------------------------------------------------------------
# 映射说明：
#   - 数值类 → number
#   - 文本 / 富文本 / 地址 / URL / 邮箱 / 电话 / 证件 / 引用类 / 组合 / 行政区划 → string
#   - 单点日期 → date；日期范围 → string（值为 [start,end]，按字符串处理）
#   - 下拉 / 列表（单选多选）→ enum（仍为 string 存储，但白名单走 enum 分支）
#   - 布尔 / 确认题 → boolean
_FIELD_TYPE_MAP: Dict[str, Dict[str, object]] = {
    'NUMBER': {'metricType': 'number', 'isEnum': False, 'label': '数值'},
    'RANGE_NUMBER': {'metricType': 'number', 'isEnum': False, 'label': '范围数值'},
    'TEXT': {'metricType': 'string', 'isEnum': False, 'label': '文本'},
    'MULTILINE_TEXT': {'metricType': 'string', 'isEnum': False, 'label': '多行文本'},
    'ADDRESS': {'metricType': 'string', 'isEnum': False, 'label': '地址'},
    'URL': {'metricType': 'string', 'isEnum': False, 'label': 'URL'},
    'EMAIL': {'metricType': 'string', 'isEnum': False, 'label': '邮箱'},
    'PHONE': {'metricType': 'string', 'isEnum': False, 'label': '电话'},
    'ID_CARD': {'metricType': 'string', 'isEnum': False, 'label': '身份证'},
    'BANK_CARD': {'metricType': 'string', 'isEnum': False, 'label': '银行卡'},
    'RICH_TEXT': {'metricType': 'string', 'isEnum': False, 'label': '富文本'},
    'PERSON': {'metricType': 'string', 'isEnum': False, 'label': '人员'},
    'DEPARTMENT': {'metricType': 'string', 'isEnum': False, 'label': '部门'},
    'REGION': {'metricType': 'string', 'isEnum': False, 'label': '行政区划'},
    'COMPOSITE': {'metricType': 'string', 'isEnum': False, 'label': '组合字段'},
    'ATTACHMENT': {'metricType': 'string', 'isEnum': False, 'label': '附件'},
    'DATE': {'metricType': 'date', 'isEnum': False, 'label': '单点日期'},
    'DATE_RANGE': {'metricType': 'string', 'isEnum': False, 'label': '日期范围'},
    'SELECT': {'metricType': 'string', 'isEnum': True, 'label': '单选'},
    'MULTISELECT': {'metricType': 'string', 'isEnum': True, 'label': '多选'},
    'LIST_SINGLE': {'metricType': 'string', 'isEnum': True, 'label': '列表单选'},
    'LIST_MULTI': {'metricType': 'string', 'isEnum': True, 'label': '列表多选'},
    'BOOLEAN': {'metricType': 'boolean', 'isEnum': False, 'label': '布尔'},
    'CONFIRM': {'metricType': 'boolean', 'isEnum': False, 'label': '确认题'},
}


def field_type_capability(field_type: str) -> Dict[str, object]:
    """动态字段类型 → 指标映射 + 运算符白名单。

    返回：{metricType, isEnum, returnTypeLabel, operators:[...]}
    未知类型兜底为 string（但绝不返回引擎不支持的运算符）。
    """
    info = _FIELD_TYPE_MAP.get(field_type, {'metricType': 'string', 'isEnum': False, 'label': '文本'})
    metric_type = info['metricType']  # type: ignore[assignment]
    is_enum = bool(info['isEnum'])  # type: ignore[arg-type]
    return {
        'metricType': metric_type,
        'isEnum': is_enum,
        'returnTypeLabel': info['label'],  # type: ignore[typeddict-item]
        'operators': operators_for(metric_type, is_enum),
    }
