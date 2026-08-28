"""校招管控 — 规则导入/导出 Excel 工具（openpyxl，零额外重依赖）。

模板与导入共用同一套列结构，保证「下载模板 → 填数据 → 导入」闭环一致。

v2.9 扁平模型：每条规则 = 独占 (适用范围·维度·指标·年度) 组合，无多指标占比分配。
  - target 写库恒为 1.0（管控占比 100%），模板不再列「目标占比」列；
  - 控制强度仅「硬约束 / 软约束」（软约束 = 原「软约束 / 仅提示」合并，后端处理一致）。

列顺序（行 = 一条规则）：
  0 维度          (dimension name)
  1 指标          (indicator name)
  2 部门          (bu；空 = 全局)
  3 职务          (position；空 = 不限)
  4 职级          (level；空 = 不限)
  5 规划年度      (year int)
  6 控制强度       (硬约束/软约束)
  7 年度目标人数    (int)
  8..19 1月..12月目标 (int)
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .constants import STRENGTH, DEPTS, POSITIONS, LEVELS, ALL_MONTHS
from .models import ControlDimension, ControlIndicator

# 列头（模板首行；v2.9 扁平模型：删「目标占比(%)」列，target 写库恒为 1.0）
HEADERS = [
    '维度', '指标', '部门', '职务', '职级', '规划年度',
    '控制强度', '年度目标人数',
    *ALL_MONTHS,  # 1月..12月
]
N_MONTH_COLS = 12
MONTH_START_COL = 8  # 第 8 列(下标)起为 1月
# 扁平模型下 target 写库恒为 1.0；模板不再要求用户填写占比列
FLAT_TARGET = 1.0

# 样式
HEADER_FILL = PatternFill('solid', fgColor='6366F1')
HEADER_FONT = Font(color='FFFFFF', bold=True, size=11)
SAMPLE_FILL = PatternFill('solid', fgColor='F1F5F9')
THIN = Side(style='thin', color='E2E8F0')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
NOTE_FILL = PatternFill('solid', fgColor='FFF7ED')
NOTE_FONT = Font(color='9A3412', size=10)


def _to_int(v, default=0):
    if v is None or v == '':
        return default
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return default


def _to_decimal_target(pct):
    """百分比字符串/数字 → Decimal(0~1)；非法返回 None。

    v2.9 扁平模型：模板不再含「目标占比」列；保留此函数仅为向后兼容旧模板/旧导出文件。
    """
    if pct is None or pct == '':
        return None
    try:
        val = Decimal(str(pct))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return val / Decimal('100')


def build_export_workbook(rules):
    """rules: list[dict]（来自 _rule_to_dict）。返回 Workbook。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '管控规则'
    ws.append(HEADERS)
    for c in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = BORDER

    for r in rules:
        mt = r.get('monthly_targets') or [0] * 12
        mt = [(mt[i] if i < len(mt) else 0) for i in range(12)]
        # v2.9：删「目标占比」导出列（target 恒 1.0 无意义）
        row = [
            r.get('dimension', ''),
            r.get('indicator', ''),
            r.get('bu', '') or '',
            r.get('position', '') or '',
            r.get('level', '') or '',
            r.get('year', ''),
            r.get('strength', ''),
            r.get('annual_target', 0),
            *mt,
        ]
        ws.append(row)

    # 列宽（v2.9：删除占比列宽；总列 = 8 + 12 = 20）
    widths = [10, 10, 10, 10, 8, 10, 10, 12] + [7] * N_MONTH_COLS
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'
    return wb


def build_template_workbook():
    """返回带表头 + 示例行 + 填写说明的模板 Workbook（v2.9 扁平模型）。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '管控规则模板'

    # 1) 说明区（v2.9 扁平模型：每条规则独占组合，无需占比加和）
    notes = [
        '填写说明：',
        '1. 每行一条规则；每条规则 = 独立的「部门+职务+职级+维度+指标+规划年度」组合，无需拆分占比。',
        '2. 维度须为系统已有维度（院校标签/专业标签/性别）；指标须属于该维度（如 985、男、工学）。',
        '3. 部门留空 = 全局；职务/职级留空 = 不限。部门须在枚举内，职务/职级可选。',
        '4. 控制强度：硬约束 / 软约束（软约束命中仅提示、放行）。',
        '5. 年度目标人数 与 12 个月目标 均填整数；12 个月目标之和须 = 年度目标人数。',
        '6. 请勿修改表头行与下方示例行以外的表结构；导入时仅读取「管控规则模板」以外的数据行。',
    ]
    for i, line in enumerate(notes, start=1):
        cell = ws.cell(row=i, column=1, value=line)
        cell.fill = NOTE_FILL
        cell.font = NOTE_FONT
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=len(HEADERS))
        cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

    header_row = len(notes) + 2  # 空一行
    for c, h in enumerate(HEADERS, start=1):
        cell = ws.cell(row=header_row, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = BORDER

    # 示例行（院校标签·985，全局，2026，硬约束，年100）— v2.9 删占比列
    example = ['院校标签', '985', '', '', '', 2026, '硬约束', 100] + [8, 8, 8, 8, 9, 9, 8, 8, 9, 9, 8, 8]
    for c, v in enumerate(example, start=1):
        cell = ws.cell(row=header_row + 1, column=c, value=v)
        cell.fill = SAMPLE_FILL
        cell.border = BORDER

    widths = [10, 10, 10, 10, 8, 10, 10, 12] + [7] * N_MONTH_COLS
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1).coordinate
    return wb, header_row


ERROR_COL = '错误原因'


def parse_import_workbook(file_obj):
    """解析上传的 xlsx，返回 (groups, errors, original_rows, errors_by_line)。

    groups: list[group_payload]，同 with_targets 入参：
        { bu, position, level, dimension(name), year, total_target, rules:[{indicator, target, strength, monthly_targets}] }
    errors: list[str]（行级/组级错误，给用户看，已带行号前缀）。
    original_rows: list[(line_no, row_values)]，保留解析时的原始数据行（含行号），用于生成融合错误报告。
    errors_by_line: dict[int, str]，行号 → 该行错误原因（组级错误映射到组内首行），用于按行融合到 Excel。
    """
    wb = load_workbook(file_obj, data_only=True)
    ws = wb.active

    # 维度/指标动态校验：一次性拉取启用集（避免每行 N+1）
    valid_dims = set(ControlDimension.objects.filter(is_active=True).values_list('name', flat=True))
    valid_ind = {
        (ind.dimension.name, ind.name)
        for ind in ControlIndicator.objects.filter(is_active=True).select_related('dimension')
    }

    # 找到表头行：含「维度」「指标」的那一行（v2.9 表头列减少，列范围 1..8）
    header_row = None
    for ridx in range(1, min(ws.max_row, 30) + 1):
        row_vals = [str(ws.cell(row=ridx, column=c).value or '').strip() for c in range(1, 9)]
        if '维度' in row_vals and '指标' in row_vals:
            header_row = ridx
            break
    if header_row is None:
        return [], ['未找到表头（需含「维度」「指标」列）'], [], {}

    groups = {}
    errors = []
    original_rows = []  # (line_no, [原始单元格值])
    errors_by_line = {}  # line_no -> 错误原因
    for ridx in range(header_row + 1, ws.max_row + 1):
        vals = [ws.cell(row=ridx, column=c).value for c in range(1, len(HEADERS) + 1)]
        if all(v is None or v == '' for v in vals[:8]):
            continue  # 空行（v2.9：HEADERS 减为 8 个基础列）
        line_no = ridx
        # 保留原始数据行（含表头列数）
        original_rows.append((line_no, vals[:len(HEADERS)]))
        dimension = str(vals[0] or '').strip()
        indicator = str(vals[1] or '').strip()
        bu = str(vals[2] or '').strip()
        position = str(vals[3] or '').strip()
        level = str(vals[4] or '').strip()
        year_raw = vals[5]
        strength = str(vals[6] or '').strip()  # v2.9：原占比列改为控制强度
        annual = _to_int(vals[7], 0)  # v2.9：年度目标人数下标 7（原 8）
        monthly = [_to_int(vals[MONTH_START_COL + i], 0) for i in range(N_MONTH_COLS)]

        # 行级基础校验：同时记录到 errors（带行号前缀，给用户看）与 errors_by_line（用于按行融合 Excel）
        def _row_err(msg: str):
            errors.append(f'第{line_no}行：{msg}')
            errors_by_line[line_no] = msg

        if not dimension:
            _row_err('维度为空'); continue
        if dimension not in valid_dims:
            _row_err(f'维度「{dimension}」非法（须为系统已启用的维度：{", ".join(sorted(valid_dims))}）'); continue
        if not indicator:
            _row_err('指标为空'); continue
        if (dimension, indicator) not in valid_ind:
            _row_err(f'指标「{indicator}」非法（维度「{dimension}」下未启用该指标）'); continue
        if bu and bu not in DEPTS:
            _row_err(f'部门「{bu}」非法（须为 {", ".join(DEPTS)} 或留空=全局）'); continue
        if position and position not in POSITIONS:
            _row_err(f'职务「{position}」非法（须为 {", ".join(POSITIONS)} 或留空=不限）'); continue
        if level and level not in LEVELS:
            _row_err(f'职级「{level}」非法（须为 {", ".join(LEVELS)} 或留空=不限）'); continue
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            _row_err(f'规划年度「{year_raw}」须为整数（如 2026）'); continue
        if strength and strength not in STRENGTH:
            _row_err(f'控制强度「{strength}」非法（须为 {", ".join(STRENGTH)}）'); continue
        if annual < 0:
            _row_err(f'年度目标人数「{annual}」不能为负'); continue
        monthly_sum = sum(monthly)
        if monthly_sum != annual:
            _row_err(
                f'12 个月目标之和（{monthly_sum}）≠ 年度目标人数（{annual}）；'
                f'请调整 1月..12月 列使加和 = 年度目标'
            ); continue

        scope_key = (bu, position, level, dimension, year)
        g = groups.setdefault(scope_key, {
            'bu': bu, 'position': position, 'level': level,
            'dimension': dimension, 'year': year,
            'total_target': 0, 'rules': [],
            'first_line': line_no,  # 组内首行行号（用于组级错误映射）
        })
        # totalTarget = 该组年度目标之和（保留字段，扁平模型下每组只有 1 条规则）
        g['total_target'] += annual
        g['rules'].append({
            'indicator': indicator,
            'target': FLAT_TARGET,  # v2.9：扁平模型 target 恒为 1.0
            'strength': strength or '硬约束',
            'monthly_targets': monthly,
            'annual_target': annual,
        })

    # v2.9：删除「目标占比之和=100%」组级校验（每条规则独占组合，无多指标占比分配）

    group_list = [g for g in groups.values()]
    return group_list, errors, original_rows, errors_by_line


def scope_text(bu, position, level):
    if not bu and not position and not level:
        return '全局'
    return ' · '.join(filter(bool, [bu, position or '职务不限', level or '职级不限']))


ERROR_FILL = PatternFill('solid', fgColor='FEE2E2')  # 浅红底标注错误行
ERROR_FONT = Font(color='B91C1C', size=11)


def build_error_report_workbook(original_rows, errors_by_line):
    """生成「融合错误报告」xlsx：保留用户上传文件的原始数据行，并在每行末尾追加「错误原因」列。

    original_rows: list[(line_no, row_values)]（来自 parse_import_workbook）。
    errors_by_line: dict[line_no -> 错误原因字符串]。
    返回 Workbook。
    """
    wb = Workbook()
    ws = wb.active
    ws.title = '导入错误明细'
    headers = list(HEADERS) + [ERROR_COL]
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HEADER_FILL if c <= len(HEADERS) else ERROR_FILL
        cell.font = HEADER_FONT if c <= len(HEADERS) else ERROR_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = BORDER

    for line_no, vals in original_rows:
        err = errors_by_line.get(line_no, '')
        row_vals = list(vals) + [err]
        ws.append(row_vals)
        excel_row = ws.max_row
        if err:
            for c in range(1, len(headers) + 1):
                ws.cell(row=excel_row, column=c).fill = ERROR_FILL
            ws.cell(row=excel_row, column=len(headers)).font = ERROR_FONT

    widths = [10, 10, 10, 10, 8, 10, 10, 12] + [7] * N_MONTH_COLS + [50]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'
    return wb


__all__ = ['build_export_workbook', 'build_template_workbook', 'parse_import_workbook',
           'build_error_report_workbook', 'HEADERS', 'ERROR_COL']
