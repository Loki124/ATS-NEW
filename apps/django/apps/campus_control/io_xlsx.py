"""校招管控 — 规则导入/导出 Excel 工具（openpyxl，零额外重依赖）。

模板与导入共用同一套列结构，保证「下载模板 → 填数据 → 导入」闭环一致。

列顺序（行 = 一条规则）：
  0 维度          (dimension name)
  1 指标          (indicator name)
  2 部门          (bu；空 = 全局)
  3 职务          (position；空 = 不限)
  4 职级          (level；空 = 不限)
  5 规划年度      (year int)
  6 目标占比(%)    (0~100，写库时 ÷100)
  7 控制强度       (硬约束/软约束/仅提示)
  8 年度目标人数    (int)
  9..20 1月..12月目标 (int)
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .constants import STRENGTH, DEPTS, POSITIONS, LEVELS, DIMS, ALL_MONTHS

# 列头（模板首行）
HEADERS = [
    '维度', '指标', '部门', '职务', '职级', '规划年度',
    '目标占比(%)', '控制强度', '年度目标人数',
    *ALL_MONTHS,  # 1月..12月
]
N_MONTH_COLS = 12
MONTH_START_COL = 9  # 第 9 列(下标)起为 1月

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
    """百分比字符串/数字 → Decimal(0~1)；非法返回 None。"""
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
        row = [
            r.get('dimension', ''),
            r.get('indicator', ''),
            r.get('bu', '') or '',
            r.get('position', '') or '',
            r.get('level', '') or '',
            r.get('year', ''),
            round(float(r.get('target', 0)) * 100, 2),
            r.get('strength', ''),
            r.get('annual_target', 0),
            *mt,
        ]
        ws.append(row)

    # 列宽
    widths = [10, 10, 10, 10, 8, 10, 12, 10, 12] + [7] * N_MONTH_COLS
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'
    return wb


def build_template_workbook():
    """返回带表头 + 示例行 + 填写说明的模板 Workbook。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '管控规则模板'

    # 1) 说明区
    notes = [
        '填写说明：',
        '1. 每行一条规则；同一「部门+职务+职级+维度+规划年度」下的所有指标，目标占比(%)之和须 = 100。',
        '2. 维度须为系统已有维度（院校标签/专业标签/性别）；指标须属于该维度（如 985、男、工学）。',
        '3. 部门留空 = 全局；职务/职级留空 = 不限。部门须在枚举内，职务/职级可选。',
        '4. 控制强度：硬约束 / 软约束 / 仅提示。',
        '5. 目标占比(%) 填 0~100 的数值（如 60 表示 60%）。',
        '6. 年度目标人数 与 12 个月目标 均填整数；12 个月目标之和须 = 年度目标人数。',
        '7. 请勿修改表头行与下方示例行以外的表结构；导入时仅读取「管控规则模板」以外的数据行。',
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

    # 示例行（院校标签·985，全局，2026）
    example = ['院校标签', '985', '', '', '', 2026, 60, '硬约束', 100] + [8, 8, 8, 8, 9, 9, 8, 8, 9, 9, 8, 8]
    for c, v in enumerate(example, start=1):
        cell = ws.cell(row=header_row + 1, column=c, value=v)
        cell.fill = SAMPLE_FILL
        cell.border = BORDER

    widths = [10, 10, 10, 10, 8, 10, 12, 10, 12] + [7] * N_MONTH_COLS
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1).coordinate
    return wb, header_row


def parse_import_workbook(file_obj):
    """解析上传的 xlsx，返回 { groups, errors }。

    groups: list[ (scope_key, group_payload) ]，group_payload 同 with_targets 入参：
        { bu, position, level, dimension(name), year, total_target, rules:[{indicator, target, strength, monthly_targets}] }
    errors: list[str]（行级/组级错误，给用户看）。
    """
    wb = load_workbook(file_obj, data_only=True)
    ws = wb.active

    # 找到表头行：含「维度」「指标」的那一行
    header_row = None
    for ridx in range(1, min(ws.max_row, 30) + 1):
        row_vals = [str(ws.cell(row=ridx, column=c).value or '').strip() for c in range(1, 10)]
        if '维度' in row_vals and '指标' in row_vals:
            header_row = ridx
            break
    if header_row is None:
        return [], ['未找到表头（需含「维度」「指标」列）']

    groups = {}
    errors = []
    for ridx in range(header_row + 1, ws.max_row + 1):
        vals = [ws.cell(row=ridx, column=c).value for c in range(1, len(HEADERS) + 1)]
        if all(v is None or v == '' for v in vals[:9]):
            continue  # 空行
        line_no = ridx
        dimension = str(vals[0] or '').strip()
        indicator = str(vals[1] or '').strip()
        bu = str(vals[2] or '').strip()
        position = str(vals[3] or '').strip()
        level = str(vals[4] or '').strip()
        year_raw = vals[5]
        target_raw = vals[6]
        strength = str(vals[7] or '').strip()
        annual = _to_int(vals[8], 0)
        monthly = [_to_int(vals[MONTH_START_COL + i], 0) for i in range(N_MONTH_COLS)]

        # 行级基础校验
        if not dimension:
            errors.append(f'第{line_no}行：维度为空')
            continue
        if dimension not in DIMS:
            errors.append(f'第{line_no}行：维度「{dimension}」非法（须为 {",".join(DIMS)}）')
            continue
        if not indicator:
            errors.append(f'第{line_no}行：指标为空')
            continue
        if bu and bu not in DEPTS:
            errors.append(f'第{line_no}行：部门「{bu}」非法')
            continue
        if position and position not in POSITIONS:
            errors.append(f'第{line_no}行：职务「{position}」非法')
            continue
        if level and level not in LEVELS:
            errors.append(f'第{line_no}行：职级「{level}」非法')
            continue
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            errors.append(f'第{line_no}行：规划年度「{year_raw}」须为整数')
            continue
        target = _to_decimal_target(target_raw)
        if target is None:
            errors.append(f'第{line_no}行：目标占比「{target_raw}」须为 0~100 的数值')
            continue
        if not (Decimal('0') <= target <= Decimal('1')):
            errors.append(f'第{line_no}行：目标占比须 0~100')
            continue
        if strength and strength not in STRENGTH:
            errors.append(f'第{line_no}行：控制强度「{strength}」非法（须为 {",".join(STRENGTH)}）')
            continue
        if sum(monthly) != annual:
            errors.append(f'第{line_no}行（{dimension}·{indicator}）：12个月目标之和({sum(monthly)})≠年度目标({annual})')
            continue

        scope_key = (bu, position, level, dimension, year)
        g = groups.setdefault(scope_key, {
            'bu': bu, 'position': position, 'level': level,
            'dimension': dimension, 'year': year,
            'total_target': 0, 'rules': [],
        })
        # totalTarget = 该组年度目标之和（用于后端 annual=round(totalTarget*target)）
        g['total_target'] += annual
        g['rules'].append({
            'indicator': indicator,
            'target': float(target),
            'strength': strength or '硬约束',
            'monthly_targets': monthly,
            'annual_target': annual,
        })

    # 组级 100% 校验
    for key, g in groups.items():
        s = sum(Decimal(str(r['target'])) for r in g['rules'])
        if abs(s - Decimal('1')) > Decimal('0.0001'):
            pct = (s * 100).quantize(Decimal('0.01'))
            bu, position, level, dimension, year = key
            scope = scope_text(bu, position, level)
            errors.append(f'组[{scope}·{dimension}·{year}]：目标占比之和须=100%，当前 {pct}%')

    group_list = [g for g in groups.values()]
    return group_list, errors


def scope_text(bu, position, level):
    if not bu and not position and not level:
        return '全局'
    return ' · '.join(filter(bool, [bu, position or '职务不限', level or '职级不限']))


__all__ = ['build_export_workbook', 'build_template_workbook', 'parse_import_workbook', 'HEADERS']
