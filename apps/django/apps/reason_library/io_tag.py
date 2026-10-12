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

import io
from typing import Dict, List

from django.core.files.uploadedfile import UploadedFile
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from apps.common.csv_safe import SafeCsvWriter
from apps.common.excel import (
    BORDER,
    SAMPLE_FILL,
    ExcelParseError,
    read_rows,
    set_column_widths,
    style_header_row,
)

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

# 列宽（与 io_indicator 对齐）
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
    for c, h in enumerate(TAG_HEADERS, start=1):
        ws.cell(row=1, column=c, value=h)
    style_header_row(ws)

    sample = [TAG_TEMPLATE_SAMPLE.get(h, '') for h in TAG_HEADERS]
    for col_idx, value in enumerate(sample, start=1):
        cell = ws.cell(row=2, column=col_idx, value=value)
        cell.fill = SAMPLE_FILL
        cell.border = BORDER
    set_column_widths(ws, COLUMN_WIDTHS)

    note_ws = wb.create_sheet(NOTE_SHEET_NAME)
    for line_no, line in enumerate(NOTE_LINES, start=1):
        cell = note_ws.cell(row=line_no, column=1, value=line)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        if line_no == 1:
            cell.font = Font(bold=True, size=12)
    note_ws.column_dimensions['A'].width = 80
    return wb


# ============================================================
#  csv 模板构建
# ============================================================
def build_tag_template_csv() -> str:
    """csv 模板内容（表头 + 1 行示例）。调用方负责加 BOM（utf-8-sig）。"""
    buf = io.StringIO()
    writer = SafeCsvWriter(buf)
    writer.writerow(TAG_HEADERS)
    writer.writerow([TAG_TEMPLATE_SAMPLE.get(h, '') for h in TAG_HEADERS])
    return buf.getvalue()


# ============================================================
#  解析（自动识别 xlsx / csv，含编码回退）
# ============================================================
def parse_tag_rows(upload: UploadedFile) -> List[Dict[str, str]]:
    """解析上传文件 → 行字典列表（键为 TAG_HEADERS 中的列名，值为字符串）。

    通过 apps.common.excel.read_rows 自动识别 ``.xlsx`` / ``.csv``（含
    utf-8-sig → gbk 编码回退、xlsx 魔数嗅探），无需按扩展名分派；
    空行跳过，行号由调用方从 2 起算（第 1 行为表头）。

    :raises TagFileParseError: 编码不支持 / 文件损坏 / 缺少必填列 name
    """
    try:
        return read_rows(
            upload,
            sheet=TAG_SHEET_NAME,
            aliases={h: (h,) for h in TAG_HEADERS},
            required=TAG_REQUIRED_HEADERS,
            columns=TAG_HEADERS,
        )
    except ExcelParseError as exc:
        raise TagFileParseError(f'文件解析失败: {exc}') from exc
