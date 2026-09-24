"""派生指标计算函数注册表（方案 A 增量 2 —— 「无需频繁开发」的分水岭）。

设计要点：
    原子指标只能"取值"，覆盖不了「最大空窗期」「近 N 年跳槽段数」「最高学历」这类
    遍历 / 聚合 / 时间窗规则 —— 而业务上高频调整的恰恰是它们。本注册表把"计算范式"
    收敛为可配置函数：

        新增一个派生指标 = 选已有函数 + 配参数   → 运营零代码完成
        新增一种计算范式 = 在此注册一个新函数     → 唯一需要开发的场景（有意为之的少数）

    新增函数只需写一个 @register 装饰的函数，**不产生迁移、不改引擎、不改已有函数**
    （开闭原则）。函数白名单由本模块动态提供，故模型层 calc_func 不设 choices。

统一签名：fn(items, params, data) -> Any
    items  = 由 DerivedMetric.base_path 解析出的值（通常是 list）
    params = DerivedMetric.params（运营配置的参数）
    data   = 完整业务数据快照（兜底用）
    返回 None 表示该指标无值（引擎按"为空"处理，不抛错）。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

REGISTRY: Dict[str, Dict[str, Any]] = {}

DEFAULT_DEGREE_ORDER: List[str] = ['其他', '高中', '大专', '本科', '硕士', '博士']


class DerivedComputeError(Exception):
    """派生指标计算失败（如函数未注册）。"""


def register(name: str, label: str, description: str = '', params_hint: str = '') -> Callable:
    """注册一个派生计算函数（幂等，同名覆盖）。"""

    def deco(fn: Callable) -> Callable:
        REGISTRY[name] = {
            'name': name,
            'label': label,
            'description': description,
            'params_hint': params_hint,
            'fn': fn,
        }
        return fn

    return deco


def get(name: str) -> Optional[Dict[str, Any]]:
    return REGISTRY.get(name)


def list_funcs() -> List[Dict[str, Any]]:
    """供前端下拉展示（不含函数引用）。"""
    return [
        {
            'name': e['name'],
            'label': e['label'],
            'description': e['description'],
            'paramsHint': e['params_hint'],
        }
        for e in REGISTRY.values()
    ]


def compute(name: str, items: Any, params: Optional[dict] = None, data: Optional[dict] = None) -> Any:
    entry = REGISTRY.get(name)
    if entry is None:
        raise DerivedComputeError(f'未注册的计算函数: {name}')
    return entry['fn'](items, params or {}, data or {})


# ---------------------------------------------------------------------------
# 内置计算函数
# ---------------------------------------------------------------------------

def _to_date(value: Any) -> Optional[date]:
    """宽松解析日期：date / datetime / ISO 字符串；失败返回 None（不抛）。"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        text = value.strip().replace('T', ' ').split(' ')[0]
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    return None


def _months_between(start: date, end: date) -> int:
    """end - start 的月数（按日补齐，可为负表示区间重叠）。"""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def _items_of(items: Any) -> List[dict]:
    if not isinstance(items, list):
        return []
    return [it for it in items if isinstance(it, dict)]


def _span(item: dict) -> Optional[tuple]:
    """取一段经历的 (start, end)；在职（无 end）按今天计。"""
    start = _to_date(item.get('start_date') or item.get('startDate'))
    if start is None:
        return None
    end = _to_date(item.get('end_date') or item.get('endDate')) or date.today()
    return (start, end)


@register(
    'MAX_GAP', '最大空窗期(月)',
    '工作经历相邻两段之间的最大间隔月数；在职段按今天计算',
    '无参数（单位固定为月）',
)
def max_gap(items: Any, params: dict, data: dict) -> int:
    """「空窗期不能超过 6 个月」—— PRD 背景规则中原子指标无法表达的一条。"""
    rows = [s for s in (_span(it) for it in _items_of(items)) if s]
    if len(rows) < 2:
        return 0
    rows.sort(key=lambda x: x[0])
    gaps = [max(_months_between(rows[i - 1][1], rows[i][0]), 0)
            for i in range(1, len(rows))]
    return max(gaps) if gaps else 0


@register(
    'COUNT_IN_WINDOW', '近N年段数',
    '统计近 N 年内开始的经历段数（跳槽频率）',
    'window_years: 年数，默认 5',
)
def count_in_window(items: Any, params: dict, data: dict) -> int:
    """「跳槽频率近 5 年不能超过 3 段」。"""
    try:
        years = int(params.get('window_years', 5) or 5)
    except (TypeError, ValueError):
        years = 5
    today = date.today()
    try:
        cutoff = date(today.year - years, today.month, today.day)
    except ValueError:  # 2 月 29 日
        cutoff = date(today.year - years, today.month, 28)

    count = 0
    for item in _items_of(items):
        span = _span(item)
        if span and span[0] >= cutoff:
            count += 1
    return count


@register(
    'HIGHEST_EDU', '最高学历',
    '教育经历中的最高学历（按学历序取最大）',
    'degree_order: 可选，自定义学历顺序数组',
)
def highest_edu(items: Any, params: dict, data: dict) -> Optional[str]:
    """「第一学历/最高学历必须是本科及以上」。"""
    order = params.get('degree_order') or DEFAULT_DEGREE_ORDER
    best: Optional[str] = None
    best_rank = -1
    for item in _items_of(items):
        degree = item.get('degree') or item.get('education') or item.get('学历')
        if not degree:
            continue
        degree = str(degree).strip()
        rank = order.index(degree) if degree in order else -1
        if rank > best_rank:
            best_rank, best = rank, degree
    return best


@register(
    'AGE_FROM_BIRTHDAY', '年龄(由生日推算)',
    '按出生日期计算周岁；解决 DB 只存 birthday 时「年龄>30」无法直接取值的问题',
    '无参数',
)
def age_from_birthday(items: Any, params: dict, data: dict) -> Optional[int]:
    raw = items[0] if isinstance(items, list) and items else items
    birthday = _to_date(raw.get('birthday') if isinstance(raw, dict) else raw)
    if birthday is None:
        return None
    today = date.today()
    return today.year - birthday.year - int((today.month, today.day) < (birthday.month, birthday.day))


@register(
    'TOTAL_WORK_MONTHS', '总工作年限(月)',
    '所有工作经历累计月数（重叠区间不去重）',
    '无参数',
)
def total_work_months(items: Any, params: dict, data: dict) -> int:
    rows = [s for s in (_span(it) for it in _items_of(items)) if s]
    return sum(max(_months_between(s, e), 0) for s, e in rows)
