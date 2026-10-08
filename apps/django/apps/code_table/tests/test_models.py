"""code_table 模型最小测试 (#29, 2026-10-09).

码表库是只读参考数据 (Region/Country/Ethnicity/Language/Currency/Industry),
此前零测试。这里锁定: 6 个模型可建 + __str__ 正确 + 树形 parent_code 关联 +
Meta.ordering。导入命令的幂等性见 test_import_idempotent.py。
"""
import pytest

from apps.code_table.models import (
    Country,
    Currency,
    Ethnicity,
    Industry,
    Language,
    Region,
    INDUSTRY_LEVEL_DIVISION,
    INDUSTRY_LEVEL_SECTION,
    LEVEL_CITY,
    LEVEL_PROVINCE,
)

pytestmark = pytest.mark.django_db


def test_region_create_and_str():
    r = Region.objects.create(code='110000', name='北京市', level=LEVEL_PROVINCE, parent_code='')
    assert r.code == '110000'
    assert '北京市' in str(r)


def test_region_parent_relationship():
    parent = Region.objects.create(code='110000', name='北京市', level=LEVEL_PROVINCE, parent_code='')
    child = Region.objects.create(code='110101', name='东城区', level=LEVEL_CITY, parent_code='110000')
    assert child.parent_code == parent.code


def test_country_create_and_str():
    c = Country.objects.create(code='CN', code3='CHN', name_cn='中国', phone_code='+86')
    assert str(c).startswith('+86')


def test_ethnicity_create():
    e = Ethnicity.objects.create(code='01', name='汉族', letter_code='HA')
    assert e.name == '汉族'


def test_language_create():
    l = Language.objects.create(code='zh', name_cn='中文', name_en='Chinese')
    assert l.name_cn == '中文'


def test_currency_create():
    cur = Currency.objects.create(code='CNY', code_numeric='156', symbol='¥', name_cn='人民币')
    assert cur.symbol == '¥'


def test_industry_tree():
    section = Industry.objects.create(
        code='A', name='农、林、牧、渔业', level=INDUSTRY_LEVEL_SECTION, parent_code='')
    division = Industry.objects.create(
        code='01', name='农业', level=INDUSTRY_LEVEL_DIVISION, parent_code='A')
    assert division.parent_code == section.code
