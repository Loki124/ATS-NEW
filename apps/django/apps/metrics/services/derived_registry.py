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
    params = 使用指标时由 MetricTemplate.calc_params 提供的实际输入值（结构由 param_schema 声明）
    data   = 完整业务数据快照（兜底用）
    返回 None 表示该指标无值（引擎按"为空"处理，不抛错）。

每个函数通过 @register 额外声明 input_kind / output_type / unit / param_schema：
    input_kind   —— 期望的 items 形状，compute() 据此做"形状不匹配"显式报错（fail-loud）
    output_type  —— 计算结果类型，供前端类型化与校验
    unit         —— 结果单位（仅展示）
    param_schema —— 参数声明，前端据此渲染类型化输入（取代自由 JSON 文本）
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

REGISTRY: Dict[str, Dict[str, Any]] = {}

DEFAULT_DEGREE_ORDER: List[str] = ['其他', '高中', '大专', '本科', '硕士', '博士']
# 「本科及以上」预设：排除大专/高中/其他，最高学历只在本科、硕士、博士中取
BACHELOR_UP_ORDER: List[str] = ['本科', '硕士', '博士']


class DerivedComputeError(Exception):
    """派生指标计算失败（如函数未注册）。"""


class InputShapeError(Exception):
    """base_path 解析结果与计算函数期望的 input_kind 不匹配。

    用于"形状不匹配"时显式报错，取代原先静默返回 0 / None 的降级——
    引擎层已用 except Exception 兜底，此类错误会降级为该步 FAIL 并带 error 文案，绝不 500。
    """


def register(
    name: str,
    label: str,
    description: str = '',
    params_hint: str = '',
    input_kind: str = '',
    output_type: str = '',
    unit: str = '',
    param_schema: Optional[List[Dict[str, Any]]] = None,
    units: Optional[List[str]] = None,
    param_units: Optional[List[str]] = None,
) -> Callable:
    """注册一个派生计算函数（幂等，同名覆盖）。

    input_kind   : 声明该函数期望 base_path 解析出的 items 形状
                   （list_periods / list_edu / date）。用于在"形状不匹配"时显式报错，
                   而非静默给出错误结果。
    output_type  : 计算结果的数据类型（number / string / boolean / date），
                   供前端类型化渲染与校验。
    unit         : 结果单位（如 月 / 岁 / 段），仅展示用。
    param_schema : 函数参数声明（[{key,label,type,options?,default?,required?}]），
                   前端据此渲染类型化参数输入，取代自由 JSON 文本。
    units        : 出参单位候选数组（模板弹窗继承栏 pill 选择；多单位才出现 pill）。
                   缺省回退为 [unit]。
    param_units  : 参数配置单位候选（仅约束「参数配置 / 取值范围」展示单位）。
    """

    def deco(fn: Callable) -> Callable:
        REGISTRY[name] = {
            'name': name,
            'label': label,
            'description': description,
            'params_hint': params_hint,
            'input_kind': input_kind,
            'output_type': output_type,
            'unit': unit,
            'param_schema': param_schema or [],
            'units': list(units) if units else ([unit] if unit else []),
            'param_units': list(param_units) if param_units else [],
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
            'inputKind': e['input_kind'],
            'outputType': e['output_type'],
            'unit': e['unit'],
            'units': e['units'],
            'paramUnits': e['param_units'],
            'paramSchema': e['param_schema'],
        }
        for e in REGISTRY.values()
    ]


def _validate_input_kind(items: Any, input_kind: str) -> None:
    """对 base_path 解析结果做形状校验（fail-loud）。

    只校验"结构性类型"，不校验"数据是否缺失"——缺失（空列表）是合法的可判空状态，
    由各函数返回 0 / None 表达，不报错。真正需要报错的是"指错了路径导致形状根本不对"。
    """
    if not input_kind:
        return
    if input_kind in ('list_periods', 'list_edu'):
        if not isinstance(items, list):
            raise InputShapeError(
                f'计算函数期望输入为列表（{input_kind}），但 base_path 解析结果为 '
                f'{type(items).__name__}，请检查数据来源路径是否指向了正确的数组字段'
            )
        # 非空却无任一对象元素：多半是指到了字符串/标量数组，配置有误
        if items and not any(isinstance(it, dict) for it in items):
            raise InputShapeError(
                f'计算函数期望输入为对象列表（{input_kind}），但解析列表的元素均非对象，'
                f'请检查 base_path 是否指向了正确的数组字段'
            )
    elif input_kind == 'date':
        resolved = items[0] if isinstance(items, list) and items else items
        ok = False
        if isinstance(resolved, dict):
            ok = _to_date(resolved.get('birthday')) is not None
        else:
            ok = _to_date(resolved) is not None
        if not ok:
            raise InputShapeError(
                f'计算函数期望输入为可解析的日期，但 base_path 解析结果为 '
                f'{items!r}，无法推算日期，请检查数据来源路径'
            )


def compute(name: str, items: Any, params: Optional[dict] = None, data: Optional[dict] = None) -> Any:
    entry = REGISTRY.get(name)
    if entry is None:
        raise DerivedComputeError(f'未注册的计算函数: {name}')
    _validate_input_kind(items, entry.get('input_kind') or '')
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
    input_kind='list_periods', output_type='number', unit='月',
    param_schema=[],
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
    input_kind='list_periods', output_type='number', unit='段',
    param_schema=[
        {
            'key': 'window_years',
            'label': '统计窗口(年)',
            'type': 'number',
            'default': 5,
            'required': False,
        },
    ],
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
    'degree_order_preset: 学历排序预设，默认 standard',
    input_kind='list_edu', output_type='string', unit='',
    param_schema=[
        {
            'key': 'degree_order_preset',
            'label': '学历排序预设',
            'type': 'select',
            'options': [
                {'value': 'standard', 'label': '标准（其他<高中<大专<本科<硕士<博士）'},
                {'value': 'bachelor_up', 'label': '本科及以上'},
            ],
            'default': 'standard',
            'required': False,
        },
    ],
)
def highest_edu(items: Any, params: dict, data: dict) -> Optional[str]:
    """「第一学历/最高学历必须是本科及以上」。"""
    order = params.get('degree_order')  # 兼容旧参数
    if not order:
        preset = params.get('degree_order_preset') or 'standard'
        order = BACHELOR_UP_ORDER if preset == 'bachelor_up' else DEFAULT_DEGREE_ORDER
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
    input_kind='date', output_type='number', unit='岁',
    param_schema=[],
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
    input_kind='list_periods', output_type='number', unit='月',
    param_schema=[],
)
def total_work_months(items: Any, params: dict, data: dict) -> int:
    rows = [s for s in (_span(it) for it in _items_of(items)) if s]
    return sum(max(_months_between(s, e), 0) for s, e in rows)


@register(
    'AVG_WORK_MONTHS', '平均工作时长',
    '平均每段工作经历的工作时长；支持最近任意段数（recent_n）与输出单位（unit：月/年），recent_n=0 表示全部工作经历',
    'recent_n: 取最近段数，0 或省略表示全部；unit: 输出单位，month=月 / year=年',
    input_kind='list_periods', output_type='number', unit='月',
    # 出参单位候选（模板弹窗继承栏 pill：月/年）；参数（recent_n 段数）单位为「段」
    units=['月', '年'], param_units=['段'],
    param_schema=[
        {
            'key': 'recent_n',
            'label': '最近段数',
            'type': 'number',
            'default': 0,
            'required': False,
        },
        {
            'key': 'unit',
            'label': '输出单位',
            'type': 'select',
            'options': [
                {'value': 'month', 'label': '月'},
                {'value': 'year', 'label': '年'},
            ],
            'default': 'month',
            'required': False,
        },
    ],
)
def avg_work_months(items: Any, params: dict, data: dict) -> float:
    """「平均每段工作时长」—— 支持最近任意段数，含全部工作经历；输出单位可切换月/年。

    recent_n=0（或省略）→ 全部工作经历求平均
    recent_n=N（正整数）→ 按开始日期降序取最近 N 段求平均
    unit='year' → 结果除以 12 以年计（保留两位小数）
    在职段（无 end_date）按今天计算时长；无有效经历返回 0（可判空，不抛错）。
    """
    try:
        recent_n = int(params.get('recent_n', 0) or 0)
    except (TypeError, ValueError):
        recent_n = 0
    unit = params.get('unit') or 'month'
    rows = [s for s in (_span(it) for it in _items_of(items)) if s]
    if not rows:
        return 0
    # 按开始日期降序取最近段数
    rows.sort(key=lambda x: x[0], reverse=True)
    if recent_n and recent_n > 0:
        rows = rows[:recent_n]
    durations = [max(_months_between(s, e), 0) for s, e in rows]
    if not durations:
        return 0
    avg_months = sum(durations) / len(durations)
    if unit == 'year':
        return round(avg_months / 12, 2)
    return round(avg_months, 1)
