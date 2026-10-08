"""code_table 导入命令幂等性测试 (#29, 2026-10-09).

审计 CODE_REVIEW 指出码表库零测试。导入命令对 currencies/industries/ethnicities
用 `bulk_create(ignore_conflicts=True)`, 重复执行不应重复插入。这里锁定
`import_code_tables` 的幂等契约 (数据来自 data_std.py 内嵌元组, 离线可跑)。
"""
import pytest
from django.core.management import call_command

from apps.code_table.models import Currency, Industry

pytestmark = pytest.mark.django_db


def test_import_currencies_idempotent():
    call_command('import_code_tables', '--only', 'currencies')
    first = Currency.objects.count()
    assert first > 0, '币种数据应成功导入'
    call_command('import_code_tables', '--only', 'currencies')
    assert Currency.objects.count() == first, '重复导入币种不得重复插入'


def test_import_industries_idempotent():
    call_command('import_code_tables', '--only', 'industries')
    first = Industry.objects.count()
    assert first > 0, '行业数据应成功导入'
    call_command('import_code_tables', '--only', 'industries')
    assert Industry.objects.count() == first, '重复导入行业不得重复插入'
