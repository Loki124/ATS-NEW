"""校招管控 v2.4 — 样本数据（§9.0 样例人员 + 默认维度/指标/规则[含人数目标]）。

v2.4 建模：
- 适用范围（bu/position/level，全空=全局）直接挂在规则上。
- 3 个维度（院校标签/专业标签/性别）；性别指标为 男/女。
- 规则：院校/专业为「全局」；性别按「部门」各一套，同(适用范围,年度)同维度加和 == 100%。
- 人数目标（年度 + 12 月）直接承载于规则上（指标层）。
"""
from .constants import DEPTS, SCHOOLS, MAJORS, SEXES  # noqa: F401


def _monthly_from_annual(annual: int) -> list:
    base = annual // 12
    rem = annual % 12
    return [base + 1 if i < rem else base for i in range(12)]


# §9.0 样例人员（31 人，[bu, school, sex, major]，统一 month=8月 / 在职 / counted）
_SAMPLE = [
    ["能电BG", "985", "男", "工学"], ["能电BG", "985", "男", "其他"], ["能电BG", "985", "男", "其他"], ["能电BG", "985", "男", "其他"],
    ["能电BG", "211", "男", "工学"], ["能电BG", "211", "男", "工学"], ["能电BG", "211", "男", "其他"], ["能电BG", "211", "男", "其他"], ["能电BG", "211", "男", "其他"],
    ["能电BG", "211", "女", "工学"], ["能电BG", "双一流", "女", "其他"], ["能电BG", "双一流", "女", "其他"],
    ["三到BG", "985", "男", "工学"], ["三到BG", "985", "男", "工学"], ["三到BG", "211", "男", "工学"], ["三到BG", "211", "男", "工学"], ["三到BG", "211", "男", "其他"], ["三到BG", "双一流", "男", "其他"],
    ["综合BG", "985", "男", "其他"], ["综合BG", "985", "男", "其他"], ["综合BG", "211", "男", "工学"], ["综合BG", "211", "男", "其他"],
    ["综合BG", "985", "女", "其他"], ["综合BG", "双一流", "女", "其他"], ["综合BG", "双一流", "女", "其他"], ["综合BG", "211", "女", "其他"],
    ["醒电BG", "985", "男", "其他"], ["醒电BG", "985", "男", "其他"], ["醒电BG", "211", "男", "工学"], ["醒电BG", "211", "女", "其他"], ["醒电BG", "双一流", "女", "其他"],
]

SAMPLE_PERSONS = []
for _i, (_bu, _school, _sex, _major) in enumerate(_SAMPLE, 1):
    SAMPLE_PERSONS.append({
        # 'code' 不再硬编码 —— 由 Person.save() 自动补号 C+8 流水号（连续且唯一）。
        'name': f'员工{_i}',
        'bu': _bu,
        'school': _school,
        'sex': _sex,
        'major': _major,
        'month': '8月',
        'status': '在职',
        'counted': True,
        'position': '',
        'level': '',
    })


# 全局维度默认指标占比（院校/专业，全公司一致）：(指标, 目标占比, 年度目标, 强度)
_SCHOOL_RULES = [
    ('985', 0.34, 40, '硬约束'),
    ('211', 0.27, 30, '硬约束'),
    ('双一流', 0.16, 20, '硬约束'),
    ('其他', 0.23, 30, '硬约束'),
]
_MAJOR_RULES = [
    ('工学', 0.35, 60, '软约束'),
    ('其他', 0.65, 60, '软约束'),
]
# 各方案性别指标占比（男+女 之和 == 100%）：(指标, 目标占比, 年度目标, 强度)
_SEX_RULES = {
    '能电BG': [('男', 0.65, 70, '硬约束'), ('女', 0.35, 50, '软约束')],
    '三到BG': [('男', 0.95, 90, '硬约束'), ('女', 0.05, 10, '硬约束')],
    '综合BG': [('男', 0.50, 60, '软约束'), ('女', 0.50, 60, '软约束')],
    '醒电BG': [('男', 0.70, 70, '软约束'), ('女', 0.30, 30, '软约束')],
}

DIMENSION_NAMES = ['院校标签', '专业标签', '性别']
INDICATOR_NAMES = {
    '院校标签': SCHOOLS,
    '专业标签': MAJORS,
    '性别': SEXES,
}


def build_rules(year: int = 2026) -> list:
    """构建全部规则（calc 用 dict 列表，含 bu/position/level/year/人数目标）。"""
    rules = []
    for ind, t, annual, st in _SCHOOL_RULES:
        rules.append({'bu': '', 'position': '', 'level': '', 'dimension': '院校标签',
                      'indicator': ind, 'year': year, 'target': t, 'strength': st,
                      'annual_target': annual, 'monthly_targets': _monthly_from_annual(annual)})
    for ind, t, annual, st in _MAJOR_RULES:
        rules.append({'bu': '', 'position': '', 'level': '', 'dimension': '专业标签',
                      'indicator': ind, 'year': year, 'target': t, 'strength': st,
                      'annual_target': annual, 'monthly_targets': _monthly_from_annual(annual)})
    for bu, sex_rules in _SEX_RULES.items():
        for ind, t, annual, st in sex_rules:
            rules.append({'bu': bu, 'position': '', 'level': '', 'dimension': '性别',
                          'indicator': ind, 'year': year, 'target': t, 'strength': st,
                          'annual_target': annual, 'monthly_targets': _monthly_from_annual(annual)})
    return rules
