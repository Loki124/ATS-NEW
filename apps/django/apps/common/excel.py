"""统一 Excel 导入/导出工具（对标 yudao ExcelUtils）。

收口项目内 10+ 处手写 openpyxl 的共性逻辑：品牌表头样式、列宽、工作表写入、
xlsx/csv 读取（含编码回退）、下载响应构建。业务模块（如 campus_control/io_xlsx、
reason_library/io_tag）改为调用本模块，消除重复的样式常量与解析胶水代码。

设计原则：
- 不引入新依赖（仅用已安装的 openpyxl，见 requirements.txt）。
- 读：自动识别 xlsx / csv；csv 优先 utf-8-sig，失败回退 gbk（老 Excel 导出常见编码）。
- 写：表头品牌色 + 白字加粗 + 居中 + 边框；列宽显式指定或自动估算；冻结首行。
- 所有公开函数纯函数式、可独立单测，不触碰 Django model（仅 build_export_response
  在调用时才惰性 import django.http）。

全站唯一入口约定（2026-10-12 收口）：
- **写入** Excel 必须经由本模块（write_sheet / build_workbook / build_export_response），
  写 CSV 必须经由 apps.common.csv_safe（SafeCsvWriter / SafeCsvDictWriter）；
  禁止在业务模块内联 openpyxl.Workbook / PatternFill / Font 或裸 csv.writer / csv.DictWriter。
- **读取** xlsx/csv 必须经由 read_rows（按列名取数）或 read_raw_rows
  （需保留表头、自定义别名/多遍解析时）；禁止业务模块内联 load_workbook。
- 样式常量（BRAND_FILL / HEADER_FONT / SAMPLE_FILL / BORDER）只定义于此，禁止他处重复。
- 测试入口为 pytest（见 pytest.ini，默认 config.settings.test / SQLite）；
  **不要**用 ``manage.py test``（默认走 dev/MySQL，测试库无建库权限会失败）。
详见同目录 EXCEL_CSV.md。
"""
from __future__ import annotations

import csv
import io
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException

# ---- 品牌样式（与 io_tag / io_xlsx 既有视觉对齐：indigo-500 表头）----
BRAND_FILL = PatternFill('solid', fgColor='6366F1')
HEADER_FONT = Font(color='FFFFFF', bold=True, size=11)
THIN = Side(style='thin', color='E2E8F0')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
SAMPLE_FILL = PatternFill('solid', fgColor='F1F5F9')

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
XLSX_EXTENSIONS = ('.xlsx', '.xlsm')
CSV_EXTENSIONS = ('.csv',)


class ExcelParseError(Exception):
    """文件解析失败（编码不支持 / 文件损坏 / 缺少必填列等）。

    由调用方捕获后统一映射为业务错误码；契约与原来各 app 自建的
    ``TagFileParseError`` 等保持一致（都是「解析失败 → 400 级错误」）。
    """


# ===========================================================================
#  写：样式 / 列宽 / 工作表 / 多表簿
# ===========================================================================
def style_header_row(
    ws,
    row: int = 1,
    *,
    fill=BRAND_FILL,
    font=HEADER_FONT,
    border=BORDER,
    align: Optional[Alignment] = None,
) -> None:
    """把指定行渲染成品牌色表头（白字加粗 + 居中 + 边框）。"""
    align = align or Alignment(horizontal='center', vertical='center')
    for cell in ws[row]:
        cell.fill = fill
        cell.font = font
        cell.border = border
        cell.alignment = align


def set_column_widths(ws, widths: Sequence[float]) -> None:
    """按列序号设置列宽（widths[0] -> A 列）。"""
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def autosize_column_widths(
    ws,
    *,
    max_width: int = 60,
    min_width: int = 8,
    sample_rows: int = 50,
) -> None:
    """按前 sample_rows 行内容自动估算列宽（CJK 字符按 2 宽）。"""
    for col_idx, col_cells in enumerate(ws.columns, start=1):
        width = min_width
        for cell in list(col_cells)[:sample_rows]:
            v = cell.value
            if v is None:
                continue
            text = str(v)
            est = sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)
            width = max(width, min(est + 2, max_width))
        ws.column_dimensions[get_column_letter(col_idx)].width = width


def write_sheet(
    ws,
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    *,
    start_row: int = 1,
    column_widths: Optional[Sequence[float]] = None,
    autosize: bool = False,
    freeze: bool = True,
    header_fill=BRAND_FILL,
    header_font=HEADER_FONT,
) -> None:
    """写一个工作表：品牌表头 + 数据行 + 列宽 + 冻结首行。

    headers/rows 为可迭代；空单元格保持为空（不强制写入）。
    """
    for c, h in enumerate(headers, start=1):
        ws.cell(row=start_row, column=c, value=h)
    style_header_row(ws, row=start_row, fill=header_fill, font=header_font)
    r = start_row + 1
    for row in rows:
        for c, val in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=val)
        r += 1
    if column_widths:
        set_column_widths(ws, column_widths)
    elif autosize:
        autosize_column_widths(ws)
    if freeze:
        ws.freeze_panes = ws.cell(row=start_row + 1, column=1).coordinate


def build_workbook(
    sheets: Dict[str, Tuple[Sequence[str], Iterable[Sequence[Any]]]],
    *,
    column_widths: Optional[Dict[str, Sequence[float]]] = None,
    autosize: bool = False,
) -> Workbook:
    """构建多工作簿。sheets: {工作表标题: (表头, 数据行)}。

    :param autosize: 未显式指定列宽时，按内容自适应列宽（用于列数/内容动态的导出，
                    如 analytics 的通用键值导出）。
    """
    wb = Workbook()
    # 去掉 load_workbook 默认创建的空 Sheet
    wb.remove(wb.active)
    for title, (headers, rows) in sheets.items():
        ws = wb.create_sheet(title=title)
        widths = (column_widths or {}).get(title)
        write_sheet(ws, headers, rows, column_widths=widths, autosize=autosize)
    return wb


def workbook_to_bytes(wb: Workbook) -> bytes:
    """Workbook -> xlsx 字节流。"""
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_export_response(wb: Workbook, filename: str):
    """构建 Django 下载响应（HttpResponse）。

    仅在 Django 运行时调用；惰性 import 避免本模块被非 Django 环境（纯单测）导入报错。
    """
    from django.http import HttpResponse

    data = workbook_to_bytes(wb)
    resp = HttpResponse(data, content_type=XLSX_CONTENT_TYPE)
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


# ===========================================================================
#  读：xlsx / csv -> 行字典列表（键为规范列名）
# ===========================================================================
def _read_source_bytes(source) -> Tuple[bytes, str]:
    """统一把来源转成 (原始字节, 文件名)；支持 bytes / 类文件对象 / 路径。"""
    if isinstance(source, (bytes, bytearray)):
        return bytes(source), ''
    if hasattr(source, 'read'):
        raw = source.read()
        if isinstance(raw, str):
            raw = raw.encode('utf-8')
        return raw, (getattr(source, 'name', '') or '')
    if isinstance(source, (str, os.PathLike)):
        path = os.fspath(source)
        with open(path, 'rb') as f:
            return f.read(), path
    raise ExcelParseError(f'不支持的导入来源类型: {type(source)!r}')


def _sniff_is_xlsx(raw: bytes, filename: str) -> bool:
    name = filename.lower()
    if name.endswith(XLSX_EXTENSIONS):
        return True
    if name.endswith(CSV_EXTENSIONS):
        return False
    # xlsx 本质是一个 ZIP 归档，魔数为 PK\x03\x04
    return raw[:2] == b'PK'


def _read_xlsx_rows(raw: bytes, *, sheet: Optional[str] = None) -> List[Tuple[Any, ...]]:
    try:
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except (InvalidFileException, BadZipFile, OSError, ValueError) as exc:  # 非法文件 / 损坏 / 格式
        raise ExcelParseError(f'Excel 文件解析失败: {exc}') from exc
    try:
        ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.active
        return [tuple(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def _read_csv_rows(raw: bytes) -> List[List[str]]:
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    text = None
    for enc in ('utf-8-sig', 'gbk'):  # 优先 utf-8-sig（去 BOM），失败回退 gbk
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ExcelParseError('CSV 编码不支持，请用 UTF-8 或 GBK')
    return [row for row in csv.reader(io.StringIO(text))]


def _detect_header_row(raw_rows: List[Any], max_scan: int = 30) -> int:
    """首行（1-based）中含 >=2 个非空单元格的那一行作为表头。

    兼容「说明区在前、表头在后」的模板（说明行通常仅 A 列有内容）。
    """
    for i, row in enumerate(raw_rows[:max_scan]):
        non_empty = sum(1 for c in row if c not in (None, ''))
        if non_empty >= 2:
            return i + 1
    return 1


def _normalize(v: Any) -> str:
    if v is None:
        return ''
    return str(v).strip()


def read_raw_rows(source, *, sheet=None) -> List[Tuple[Any, ...]]:
    """读取 xlsx / csv -> 原始行列表（含表头行，每行是 tuple）。

    与 read_rows 不同，本函数**保留表头行**、不对单元格做别名映射或规范化，
    返回原始单元格元组，供需要自定义表头映射 / 别名兼容 / 多遍解析
    （如院校库导入的撞码合并）的调用方使用。

    等效于 openpyxl ``load_workbook(read_only=True, data_only=True)``
    + ``ws.iter_rows(values_only=True)``，集中维护 openpyxl 读取样板。
    """
    raw, filename = _read_source_bytes(source)
    is_xlsx = _sniff_is_xlsx(raw, filename)
    if is_xlsx:
        return _read_xlsx_rows(raw, sheet=sheet)
    return [tuple(r) for r in _read_csv_rows(raw)]


def read_rows(
    source,
    *,
    sheet: Optional[str] = None,
    aliases: Optional[Dict[str, Sequence[str]]] = None,
    required: Optional[Sequence[str]] = None,
    columns: Optional[Sequence[str]] = None,
    skip_blank: bool = True,
    header_row: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """读取 xlsx / csv -> 行字典列表（键为规范列名）。

    :param source: 文件路径 / bytes / 类文件对象（含 .name，用于判断扩展名）。
    :param sheet: xlsx 工作表名；缺省取 active（通常即数据表）。
    :param aliases: {规范列名: (候选表头1, 候选表头2, ...)}，用于兼容中英文表头。
    :param required: 必填规范列；缺失抛 ExcelParseError。
    :param columns: 若指定，仅读取这些规范列（忽略其它列）；否则读取全部表头。
    :param skip_blank: 全空行跳过。
    :param header_row: 指定表头行（1-based）；缺省自动探测。
    :return: list[dict]，缺失单元格为 ''（与 csv.DictReader 一致）。
    """
    raw, filename = _read_source_bytes(source)
    is_xlsx = _sniff_is_xlsx(raw, filename)
    raw_rows = _read_xlsx_rows(raw, sheet=sheet) if is_xlsx else _read_csv_rows(raw)
    if not raw_rows:
        raise ExcelParseError('文件为空，未找到表头行')

    if header_row is None:
        header_row = _detect_header_row(raw_rows)
    header_fields = [_normalize(h) for h in raw_rows[header_row - 1]]
    header_index = {h: i for i, h in enumerate(header_fields) if h}

    aliases = aliases or {}
    mapping: Dict[str, int] = {}
    if columns is not None:
        for canon in columns:
            for c in aliases.get(canon, (canon,)):
                if c in header_index:
                    mapping[canon] = header_index[c]
                    break
    else:
        for h, i in header_index.items():
            if h:
                mapping[h] = i
        for canon, cands in aliases.items():
            for c in cands:
                if c in header_index:
                    mapping[canon] = header_index[c]
                    break

    required = required or []
    missing = [r for r in required if r not in mapping]
    if missing:
        raise ExcelParseError(f'缺少必填列: {", ".join(missing)} (当前列: {header_fields})')

    rows: List[Dict[str, Any]] = []
    for raw_row in raw_rows[header_row:]:
        values = {
            canon: (_normalize(raw_row[idx]) if idx < len(raw_row) else '')
            for canon, idx in mapping.items()
        }
        # 指定 columns 时，保证每一行列键齐全（缺失列补空串），
        # 与 csv.DictReader + _build_row 的「全列填充」契约一致。
        if columns is not None:
            for c in columns:
                values.setdefault(c, '')
        if skip_blank and all(v == '' for v in values.values()):
            continue
        rows.append(values)
    return rows


__all__ = [
    'ExcelParseError',
    'BRAND_FILL', 'HEADER_FONT', 'BORDER', 'SAMPLE_FILL',
    'XLSX_CONTENT_TYPE', 'XLSX_EXTENSIONS', 'CSV_EXTENSIONS',
    'style_header_row', 'set_column_widths', 'autosize_column_widths',
    'write_sheet', 'build_workbook', 'workbook_to_bytes', 'build_export_response',
    'read_rows', 'read_raw_rows',
]
