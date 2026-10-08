"""校招管控 — 指标导入/导出工具（xlsx + csv 双格式，零额外重依赖）。

与 io_xlsx（规则）保持一致的设计：模板与导入共用同一套列结构，保证
「下载模板 → 填数据 → 导入」闭环一致。

列结构（行 = 一条指标）：
  0 维度        (dimension name，须已存在)
  1 指标名称     (indicator name，同维度下唯一)
  2 是否启用     (是/否/true/false/1/0/启用/停用)

导出额外包含「完整字段信息」：维度、指标名称、是否启用三列即指标的全部业务字段。
指标ID 为内部 nanoid，不对外暴露，故不参与导入/导出（避免误导用户以为可驱动更新）。
"""
import csv
import io
import json
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException

# ---- 列头（模板首行 / 导出首行 一致） ----
INDICATOR_HEADERS = ['维度', '指标名称', '是否启用']

# 样式（与 io_xlsx 对齐视觉）
HEADER_FILL = PatternFill('solid', fgColor='6366F1')
HEADER_FONT = Font(color='FFFFFF', bold=True, size=11)
SAMPLE_FILL = PatternFill('solid', fgColor='F1F5F9')
THIN = Side(style='thin', color='E2E8F0')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
NOTE_FILL = PatternFill('solid', fgColor='FFF7ED')

BOOL_TRUE = ('是', '启用', 'true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES', 'y', 'Y')
BOOL_FALSE = ('否', '停用', 'false', 'False', 'FALSE', '0', 'no', 'No', 'NO', 'n', 'N')


def _parse_bool(raw):
    """解析「是否启用」为 bool。空 → True（默认启用）；非法 → None。"""
    if raw is None:
        return True
    v = str(raw).strip()
    if v == '':
        return True
    if v in BOOL_TRUE:
        return True
    if v in BOOL_FALSE:
        return False
    return None


def _bool_to_text(v):
    return '是' if v else '否'


# ============================================================
#  xlsx 构建
# ============================================================
def build_indicator_export_workbook(rows):
    """rows: list[{dimension_name, name, is_active(bool)}] → xlsx 工作簿。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '指标'
    _write_header(ws)
    for i, r in enumerate(rows):
        row_idx = i + 2
        ws.cell(row=row_idx, column=1, value=r.get('dimension_name', ''))
        ws.cell(row=row_idx, column=2, value=r.get('name', ''))
        ws.cell(row=row_idx, column=3, value=_bool_to_text(r.get('is_active')))
        for c in range(1, 4):
            ws.cell(row=row_idx, column=c).border = BORDER
    _style_sheet(ws)
    return wb


def build_indicator_template_workbook():
    """指标导入模板：表头 + 1 行示例 + 填写说明表。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '指标'
    _write_header(ws)
    sample = ['性别', '男', '是']
    for c, val in enumerate(sample, start=1):
        cell = ws.cell(row=2, column=c, value=val)
        cell.fill = SAMPLE_FILL
        cell.border = BORDER
    _style_sheet(ws)

    note_ws = wb.create_sheet('填写说明')
    notes = [
        '【指标导入模板】',
        '1. 每行一条指标，列顺序：维度 / 指标名称 / 是否启用。',
        '2. 「维度」必须已在系统中存在（如 性别 / 院校标签 / 专业标签），否则该行报错。',
        '3. 「指标名称」在同一维度下不可重复，长度 ≤ 32。',
        '4. 「是否启用」填写：是 / 否 / true / false / 1 / 0 / 启用 / 停用（留空默认=是）。',
        '5. 重复项处理由导入时的 mode 决定：skip=跳过已存在 / update=更新已存在 / error=遇重复即报错。',
        '6. 请勿修改首行表头，不要保留空白示例行以外的无关内容。',
    ]
    for i, line in enumerate(notes, start=1):
        cell = note_ws.cell(row=i, column=1, value=line)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        if i == 1:
            cell.font = Font(bold=True, size=12)
    note_ws.column_dimensions['A'].width = 80
    return wb


def build_indicator_error_report_workbook(original_rows, errors_by_line):
    """导入失败错误报告 xlsx。original_rows: list[{line, dimension_name, name, is_active_raw}]。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '错误明细'
    headers = ['行号', '维度', '指标名称', '是否启用', '错误原因']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER
    for i, r in enumerate(original_rows, start=2):
        ws.cell(row=i, column=1, value=r.get('line'))
        ws.cell(row=i, column=2, value=r.get('dimension_name', ''))
        ws.cell(row=i, column=3, value=r.get('name', ''))
        ws.cell(row=i, column=4, value=r.get('is_active_raw', ''))
        ws.cell(row=i, column=5, value=errors_by_line.get(r.get('line'), ''))
        for c in range(1, 6):
            ws.cell(row=i, column=c).border = BORDER
    for c, w in enumerate([8, 16, 20, 12, 60], start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    return wb


def _write_header(ws):
    for c, h in enumerate(INDICATOR_HEADERS, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER
        cell.alignment = Alignment(horizontal='center')


def _style_sheet(ws):
    for c, w in enumerate([20, 24, 12], start=1):
        ws.column_dimensions[get_column_letter(c)].width = w


# ============================================================
#  csv 构建
# ============================================================
def build_indicator_export_csv(rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(INDICATOR_HEADERS)
    for r in rows:
        writer.writerow([r.get('dimension_name', ''), r.get('name', ''), _bool_to_text(r.get('is_active'))])
    return buf.getvalue()


def build_indicator_template_csv():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(INDICATOR_HEADERS)
    writer.writerow(['性别', '男', '是'])
    return buf.getvalue()


def build_indicator_error_report_csv(original_rows, errors_by_line):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['行号', '维度', '指标名称', '是否启用', '错误原因'])
    for r in original_rows:
        writer.writerow([
            r.get('line'), r.get('dimension_name', ''), r.get('name', ''),
            r.get('is_active_raw', ''), errors_by_line.get(r.get('line'), ''),
        ])
    return buf.getvalue()


# ============================================================
#  解析（xlsx / csv 自动识别）
# ============================================================
def parse_indicator_file(file_obj):
    """解析上传文件，返回 (rows, parse_errors, original_rows, errors_by_line)。

    rows: list[{dimension_name, name, is_active_raw, line}]
    original_rows: list[{line, dimension_name, name, is_active_raw}]  (供错误报告)
    errors_by_line: dict[line, error_msg]  (解析级错误，如缺列)
    parse_errors: list[str]
    """
    name = (getattr(file_obj, 'name', '') or '').lower()
    if name.endswith('.csv'):
        return _parse_csv(file_obj)
    if name.endswith(('.xlsx', '.xlsm')):
        return _parse_xlsx(file_obj)
    return [], [f'不支持的文件类型：{file_obj.name}，仅支持 .xlsx / .csv'], [], {}


def _normalize_row(dim_name, name, is_active_raw, line):
    return {
        'dimension_name': (dim_name or '').strip(),
        'name': (name or '').strip(),
        'is_active_raw': (is_active_raw or '').strip(),
        'line': line,
    }


def _parse_xlsx(file_obj):
    rows, parse_errors, original_rows, errors_by_line = [], [], [], {}
    try:
        wb = load_workbook(file_obj, read_only=True, data_only=True)
    except (InvalidFileException, BadZipFile, OSError, ValueError) as e:  # openpyxl Excel 解析异常 (非法文件/BadZip/IO/格式) 统一兜底返错误列表
        return [], [f'Excel 文件解析失败：{e}'], [], {}
    ws = wb['指标'] if '指标' in wb.sheetnames else wb.active
    iter_rows = ws.iter_rows(values_only=True)
    try:
        header = next(iter_rows)
    except StopIteration:
        return [], ['文件为空，未找到表头行'], [], {}
    header_map = {}
    for idx, h in enumerate(header):
        if h is None:
            continue
        key = str(h).strip()
        if key in INDICATOR_HEADERS:
            header_map[key] = idx
    if '维度' not in header_map or '指标名称' not in header_map:
        return [], ['表头缺少必需的「维度」「指标名称」列'], [], {}
    col_dim = header_map['维度']
    col_name = header_map['指标名称']
    col_active = header_map.get('是否启用')

    line_no = 1  # 数据行号（与 Excel 行号对应，header 为第 1 行，数据从第 2 行起）
    for raw in iter_rows:
        line_no += 1
        dim_name = raw[col_dim] if col_dim < len(raw) else None
        name = raw[col_name] if col_name < len(raw) else None
        is_active_raw = raw[col_active] if (col_active is not None and col_active < len(raw)) else ''
        # 跳过完全空行
        if (dim_name is None or str(dim_name).strip() == '') and (name is None or str(name).strip() == ''):
            continue
        rec = _normalize_row(dim_name, name, is_active_raw, line_no)
        original_rows.append({
            'line': line_no,
            'dimension_name': rec['dimension_name'],
            'name': rec['name'],
            'is_active_raw': rec['is_active_raw'],
        })
        rows.append(rec)
    return rows, parse_errors, original_rows, errors_by_line


def _parse_csv(file_obj):
    rows, parse_errors, original_rows, errors_by_line = [], [], [], {}
    try:
        content = file_obj.read()
        if isinstance(content, bytes):
            text = content.decode('utf-8-sig')
        else:
            text = content
        reader = csv.DictReader(io.StringIO(text))
        field_map = {}
        for i, f in enumerate(reader.fieldnames or []):
            key = (f or '').strip()
            if key in INDICATOR_HEADERS:
                field_map[key] = f
        if '维度' not in field_map or '指标名称' not in field_map:
            return [], ['表头缺少必需的「维度」「指标名称」列'], [], {}
        col_dim = field_map['维度']
        col_name = field_map['指标名称']
        col_active = field_map.get('是否启用')
    except (csv.Error, ValueError, OSError) as e:  # csv 解析异常统一兜底返错误列表
        return [], [f'CSV 文件解析失败：{e}'], [], {}

    line_no = 1  # DictReader 从第 2 行起为数据（第 1 行为表头）
    for raw in reader:
        line_no += 1
        dim_name = raw.get(col_dim)
        name = raw.get(col_name)
        is_active_raw = raw.get(col_active) if col_active else ''
        if (dim_name is None or str(dim_name).strip() == '') and (name is None or str(name).strip() == ''):
            continue
        rec = _normalize_row(dim_name, name, is_active_raw, line_no)
        original_rows.append({
            'line': line_no,
            'dimension_name': rec['dimension_name'],
            'name': rec['name'],
            'is_active_raw': rec['is_active_raw'],
        })
        rows.append(rec)
    return rows, parse_errors, original_rows, errors_by_line
