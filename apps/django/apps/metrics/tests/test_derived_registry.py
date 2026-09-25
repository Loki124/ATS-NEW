"""派生指标计算函数单元测试 —— 覆盖 PRD §2.1 里原子指标表达不了的三类规则。"""
from datetime import date

import pytest

from apps.metrics.services.derived_registry import (
    DerivedComputeError,
    InputShapeError,
    compute,
    list_funcs,
)

WORKS = [
    {'start_date': '2020-01-01', 'end_date': '2021-01-01'},
    {'start_date': '2021-07-01', 'end_date': '2022-01-01'},
]


def test_max_gap():
    """「空窗期不能超过 6 个月」—— 两段间隔 6 个月。"""
    assert compute('MAX_GAP', WORKS) == 6


def test_max_gap_single_segment_is_zero():
    assert compute('MAX_GAP', [WORKS[0]]) == 0


def test_count_in_window():
    """「近 5 年跳槽不超过 3 段」。"""
    items = [
        {'start_date': '2024-01-01'},
        {'start_date': '2025-06-01'},
        {'start_date': '2019-01-01'},  # 窗口外，不计
    ]
    assert compute('COUNT_IN_WINDOW', items, {'window_years': 5}) == 2


def test_highest_edu():
    """「最高学历本科及以上」。"""
    items = [{'degree': '本科'}, {'degree': '硕士'}, {'degree': '大专'}]
    assert compute('HIGHEST_EDU', items) == '硕士'


def test_age_from_birthday():
    """DB 只存 birthday 时，「年龄 > 30」靠此函数取值。"""
    today = date.today()
    expected = today.year - 1990 - int((today.month, today.day) < (5, 20))
    assert compute('AGE_FROM_BIRTHDAY', {'birthday': '1990-05-20'}) == expected


def test_total_work_months():
    assert compute('TOTAL_WORK_MONTHS', WORKS) == 18


def test_unregistered_function_raises():
    with pytest.raises(DerivedComputeError):
        compute('NOT_A_FUNC', WORKS)


def test_empty_input_is_forgiving():
    """数据缺失不抛错，返回可判空的值。"""
    assert compute('MAX_GAP', []) == 0
    assert compute('HIGHEST_EDU', []) is None


def test_registry_exposes_builtin_funcs():
    names = {f['name'] for f in list_funcs()}
    assert {'MAX_GAP', 'COUNT_IN_WINDOW', 'HIGHEST_EDU', 'AGE_FROM_BIRTHDAY'} <= names
    # 注册表项不含函数引用，保证可 JSON 序列化给前端
    for f in list_funcs():
        assert 'fn' not in f


def test_list_funcs_carries_metadata():
    """每个函数必须声明 input_kind / output_type / param_schema（前端类型化输入依赖）。"""
    by_name = {f['name']: f for f in list_funcs()}
    for name in ('MAX_GAP', 'COUNT_IN_WINDOW', 'HIGHEST_EDU', 'AGE_FROM_BIRTHDAY', 'TOTAL_WORK_MONTHS'):
        meta = by_name[name]
        assert 'inputKind' in meta and meta['inputKind']
        assert 'outputType' in meta and meta['outputType']
        assert 'paramSchema' in meta and isinstance(meta['paramSchema'], list)
    # COUNT_IN_WINDOW 必须声明 window_years 数字参数
    cw = by_name['COUNT_IN_WINDOW']
    assert any(p['key'] == 'window_years' and p['type'] == 'number' for p in cw['paramSchema'])
    # HIGHEST_EDU 必须声明 degree_order_preset 下拉参数
    he = by_name['HIGHEST_EDU']
    assert any(p['key'] == 'degree_order_preset' and p['type'] == 'select' for p in he['paramSchema'])


def test_input_shape_error_on_non_list():
    """list_periods 函数收到非列表（指错路径）应显式报错，而非静默返回 0。"""
    with pytest.raises(InputShapeError):
        compute('MAX_GAP', {'not': 'a list'})


def test_input_shape_error_on_non_dict_list():
    """list_periods 函数收到全是标量的列表（指错路径）应显式报错。"""
    with pytest.raises(InputShapeError):
        compute('MAX_GAP', ['a', 'b', 'c'])


def test_date_shape_error_on_unparseable():
    """date 函数收到无法解析为日期的值应显式报错。"""
    with pytest.raises(InputShapeError):
        compute('AGE_FROM_BIRTHDAY', 'not-a-date')


def test_highest_edu_bachelor_up_preset():
    """本科及以上预设：大专/高中/其他不计入，无本科时返回 None。"""
    items = [{'degree': '大专'}, {'degree': '高中'}]  # 无本科及以上
    # 标准预设：大专算作有效最高学历
    assert compute('HIGHEST_EDU', items) == '大专'
    # 本科及以上预设：大专/高中不计入 → 无有效学历
    assert compute('HIGHEST_EDU', items, {'degree_order_preset': 'bachelor_up'}) is None
    # 兼容旧 degree_order 参数
    assert compute('HIGHEST_EDU', items, {'degree_order': ['本科', '硕士', '博士']}) is None
    # 含本科时两种预设都返回本科
    with_bachelor = [{'degree': '大专'}, {'degree': '本科'}]
    assert compute('HIGHEST_EDU', with_bachelor) == '本科'
    assert compute('HIGHEST_EDU', with_bachelor, {'degree_order_preset': 'bachelor_up'}) == '本科'
