"""原因标签 — 导入/模板工具（xlsx + csv 双格式）。

设计原则与 ``apps.campus_control.io_indicator`` 完全对齐：

    「模板与导入共用同一套列结构，保证『下载模板 → 填数据 → 导入』闭环一致。」

列结构（行 = 一条标签，与 CSV 历史模板一致，**不改名以免老用户模板失效**）：
    name     必填，标签名称（库内不可重复，含软删）
    en_name  可选，英文名称（≤64）
    tip      可选，鼠标悬停提示（≤128）
    type     可选，仅允许 custom（系统预置不可灌入），缺省 custom
    enabled  可选，true/false/1/0/yes/no，缺省 true

对外接口：
    build_tag_template_workbook()  → openpyxl.Workbook（xlsx 模板）
    build_tag_template_csv()       → str（csv 模板内容，调用方负责加 BOM）
    parse_tag_rows(upload)         → List[dict]，按扩展名自动分派 xlsx / csv
"""
from __future__ import annotations

import csv
import io
from typing import Dict, List
from zipfile import BadZipFile

from django.core.files.uploadedfile import UploadedFile
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException

# ---- 列定义（模板生成 + 导入解析共用同一份，避免两边漂移） ----
TAG_HEADERS: List[str] = ['name', 'en_name', 'tip', 'type', 'enabled']
TAG_REQUIRED_HEADERS: List[str] = ['name']
TAG_TEMPLATE_SAMPLE: Dict[str, str] = {
    'name': '示例标签',
    'en_name': 'Example tag',
    'tip': '鼠标悬停提示(可空)',
    'type': 'custom',
    'enabled': 'true',
}

# 工作表名（用户改表头不影响解析，但存在时优先取该表）
TAG_SHEET_NAME = '原因标签'
NOTE_SHEET_NAME = '填写说明'

# 扩展名 → 解析方式分派
XLSX_EXTENSIONS = ('.xlsx', '.xlsm')
CSV_EXTENSIONS = ('.csv',)

# 样式（与 io_indicator 对齐视觉：品牌色表头 + 浅色示例 + 橙色说明）
HEADER_FILL = PatternFill('solid', fgColor='6366F1')
HEADER_FONT = Font(color='FFFFFF', bold=True, size=11)
SAMPLE_FILL = PatternFill('solid', fgColor='F1F5F9')
THIN = Side(style='thin', color='E2E8F0')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
COLUMN_WIDTHS = [24, 24, 32, 12, 12]

NOTE_LINES = [
    '【原因标签导入模板】',
    '1. 每行一条标签，列顺序：name / en_name / tip / type / enabled（首行表头请勿修改或删除）。',
    '2. name（必填）：标签名称，在同一原因库内不可重复（含已删除的历史标签）。',
    '3. en_name：英文名称，可留空，长度 ≤ 64。',
    '4. tip：鼠标悬停提示，可留空，长度 ≤ 128。',
    '5. type：仅允许 custom（系统预置标签不可通过导入创建），可留空 → 按 custom 处理。',
    '6. enabled：true/false（也支持 1/0/yes/no），可留空 → 按启用处理。',
    '7. 空白行会被自动跳过，不会计为错误。',
    '8. 支持 .xlsx 与 .csv 两种文件格式；CSV 请使用 UTF-8 或 GBK 编码。',
]


class TagFileParseError(Exception):
    """导入文件解析失败（编码错误 / 缺列 / Excel 损坏等）。

    由 view 层捕获后统一映射为 BizCode.CSV_FORMAT_INVALID (40002)，
    契约保持不变（前端按该码走分支）。
    """


# ============================================================
#  xlsx 模板构建
# ============================================================
def build_tag_template_workbook() -> Workbook:
    """标签导入模板：表头 + 1 行示例 + 填写说明工作表。"""
    wb = Workbook()
    ws = wb.active
    ws.title = TAG_SHEET_NAME
    _write_header(ws)

    sample = [TAG_TEMPLATE_SAMPLE.get(h, '') for h in TAG_HEADERS]
    for col_idx, value in enumerate(sample, start=1):
        cell = ws.cell(row=2, column=col_idx, value=value)
        cell.fill = SAMPLE_FILL
        cell.border = BORDER
    _style_sheet(ws)

    note_ws = wb.create_sheet(NOTE_SHEET_NAME)
    for line_no, line in enumerate(NOTE_LINES, start=1):
        cell = note_ws.cell(row=line_no, column=1, value=line)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        if line_no == 1:
            cell.font = Font(bold=True, size=12)
    note_ws.column_dimensions['A'].width = 80
    return wb


def _write_header(ws) -> None:
    """写首行表头（品牌色 + 白字加粗 + 居中）。"""
    for col_idx, header in enumerate(TAG_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER
        cell.alignment = Alignment(horizontal='center')


def _style_sheet(ws) -> None:
    """列宽统一，避免内容被截断。"""
    for col_idx, width in enumerate(COLUMN_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width


# ============================================================
#  csv 模板构建
# ============================================================
def build_tag_template_csv() -> str:
    """csv 模板内容（表头 + 1 行示例）。调用方负责加 BOM（utf-8-sig）。"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(TAG_HEADERS)
    writer.writerow([TAG_TEMPLATE_SAMPLE.get(h, '') for h in TAG_HEADERS])
    return buf.getvalue()


# ============================================================
#  解析（按扩展名自动分派）
# ============================================================
def parse_tag_rows(upload: UploadedFile) -> List[Dict[str, str]]:
    """解析上传文件 → 行字典列表（键为 TAG_HEADERS 中的列名，值为字符串）。

    - ``.xlsx`` / ``.xlsm`` → openpyxl 读首个数据工作表
    - 其余（含 ``.csv``）      → 文本.decode('utf-8-sig')，失败回退 gbk

    两条路径统一产出 ``[{name, en_name, tip, type, enabled}, ...]``，
    空行跳过，行号由调用方从 2 起算（第 1 行为表头）。

    :raises TagFileParseError: 编码不支持 / 文件损坏 / 缺少必填列 name
    """
    filename = (getattr(upload, 'name', '') or '').lower()
    if filename.endswith(XLSX_EXTENSIONS):
        return _parse_xlsx_rows(upload)
    return _parse_csv_rows(upload)


def _cell_to_text(value) -> str:
    """单元格 → 文本：None → ''，bool/数字 → str（供 enabled 布尔解析使用）。"""
    if value is None:
        return ''
    return str(value)


def _is_blank_row(values: Dict[str, str]) -> bool:
    """整行为空（仅空白字符）→ True，导入时跳过而非报错。"""
    return all((v or '').strip() == '' for v in values.values())


def _build_row(values: Dict[str, str]) -> Dict[str, str]:
    """补齐所有列键，缺失为空串（与 csv.DictReader 行为一致）。"""
    return {h: values.get(h, '') or '' for h in TAG_HEADERS}


def _parse_xlsx_rows(upload: UploadedFile) -> List[Dict[str, str]]:
    try:
        raw_bytes = upload.read()
        wb = load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    except (InvalidFileException, BadZipFile, OSError, ValueError) as exc:  # openpyxl/IO 异常 (非法文件/BadZip/IO/格式) 统一兜底
        raise TagFileParseError(f'Excel 文件解析失败: {exc}') from exc

    rows: List[Dict[str, str]] = []
    try:
        ws = wb[TAG_SHEET_NAME] if TAG_SHEET_NAME in wb.sheetnames else wb.active
        iter_rows = ws.iter_rows(values_only=True)
        try:
            header = next(iter_rows)
        except StopIteration:
            raise TagFileParseError('文件为空, 未找到表头行') from None

        header_map: Dict[str, int] = {}
        for idx, raw_header in enumerate(header or ()):
            key = _cell_to_text(raw_header).strip()
            if key in TAG_HEADERS:
                header_map[key] = idx
        missing = [h for h in TAG_REQUIRED_HEADERS if h not in header_map]
        if missing:
            headers_found = [_cell_to_text(h).strip() for h in (header or ())]
            raise TagFileParseError(
                f'缺少必填列 {"/".join(missing)} (当前列: {headers_found})',
            )

        for raw_row in iter_rows:
            values: Dict[str, str] = {}
            for col, idx in header_map.items():
                values[col] = _cell_to_text(raw_row[idx]) if idx < len(raw_row) else ''
            row = _build_row(values)
            if _is_blank_row(row):
                continue
            rows.append(row)
    finally:
        try:
            wb.close()
        except OSError:  # 关闭失败不影响已解析结果
            pass
    return rows


def _parse_csv_rows(upload: UploadedFile) -> List[Dict[str, str]]:
    """CSV：utf-8-sig 优先，失败回退 gbk（老项目 Excel 导出的常见编码）。"""
    try:
        raw_bytes = upload.read()
    except (OSError, ValueError) as exc:  # 文件读取异常 (IOError/UnicodeDecodeError) 统一包成 TagFileParseError
        raise TagFileParseError(f'文件读取失败: {exc}') from exc
    if isinstance(raw_bytes, str):  # 兼容测试桩直接传文本的场景
        raw_bytes = raw_bytes.encode('utf-8')
    text = None
    for encoding in ('utf-8-sig', 'gbk'):
        try:
            text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise TagFileParseError('CSV 编码不支持, 请用 UTF-8 或 GBK')

    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = [(f or '').strip() for f in (reader.fieldnames or [])]
        missing = [h for h in TAG_REQUIRED_HEADERS if h not in fieldnames]
        if missing:
            raise TagFileParseError(
                f'缺少必填列 {"/".join(missing)} (当前列: {fieldnames})',
            )
    except TagFileParseError:
        raise
    except (csv.Error, ValueError, OSError) as exc:  # csv 方言异常统一包成 TagFileParseError
        raise TagFileParseError(f'CSV 解析失败: {exc}') from exc

    rows: List[Dict[str, str]] = []
    for raw in reader:
        values = {
            (k or '').strip(): v
            for k, v in raw.items()
            if k is not None and (k or '').strip() in TAG_HEADERS
        }
        row = _build_row({k: _cell_to_text(v) for k, v in values.items()})
        if _is_blank_row(row):
            continue
        rows.append(row)
    return rows
