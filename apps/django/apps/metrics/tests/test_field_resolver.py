"""FieldResolver 单元测试 —— 点路径 / 数组下标 / 路径穿越防护 / 类型转换。"""
from datetime import date

import pytest

from apps.metrics.services.field_resolver import (
    FieldResolveError,
    FieldResolverRegistry,
    TypeCastError,
    type_cast,
)

DATA = {
    'candidate': {
        'age': 32,
        'name': '张三',
        'workExperience': [
            {'company': 'A', 'start_date': '2020-01-01', 'end_date': '2021-01-01'},
            {'company': 'B', 'start_date': '2021-07-01', 'end_date': '2022-01-01'},
        ],
    }
}


def test_dot_path():
    assert FieldResolverRegistry.resolve('candidate.age', DATA) == 32


def test_array_index():
    """PRD T03 用例：candidate.workExperience.0.company → 'A'"""
    assert FieldResolverRegistry.resolve('candidate.workExperience.0.company', DATA) == 'A'
    assert FieldResolverRegistry.resolve('candidate.workExperience.1.company', DATA) == 'B'


def test_missing_field_raises():
    with pytest.raises(FieldResolveError):
        FieldResolverRegistry.resolve('candidate.notExist', DATA)


def test_path_without_dot_raises():
    """source_path 必须含 '.'（PRD F-02 校验在序列化层，解析层同步兜底）。"""
    with pytest.raises(FieldResolveError):
        FieldResolverRegistry.resolve('age', DATA)


def test_dunder_segment_rejected():
    """路径穿越防护：拒绝 __class__ / __proto__ 等 dunder 段。"""
    with pytest.raises(FieldResolveError):
        FieldResolverRegistry.resolve('candidate.__class__', DATA)


def test_index_out_of_range():
    with pytest.raises(FieldResolveError):
        FieldResolverRegistry.resolve('candidate.workExperience.9.company', DATA)


def test_non_index_on_list():
    with pytest.raises(FieldResolveError):
        FieldResolverRegistry.resolve('candidate.workExperience.company', DATA)


def test_type_cast_number():
    assert type_cast('32', 'number') == 32
    assert type_cast('32.5', 'number') == 32.5


def test_type_cast_number_invalid():
    with pytest.raises(TypeCastError):
        type_cast('abc', 'number')


def test_type_cast_boolean():
    assert type_cast('yes', 'boolean') is True
    assert type_cast('0', 'boolean') is False


def test_type_cast_date():
    assert type_cast('1990-05-20', 'date') == date(1990, 5, 20)


def test_type_cast_empty_passthrough():
    """空值不下抛错 —— 交由 IS_EMPTY / IS_NOT_EMPTY 判定。"""
    assert type_cast(None, 'number') is None
    assert type_cast('', 'number') == ''
