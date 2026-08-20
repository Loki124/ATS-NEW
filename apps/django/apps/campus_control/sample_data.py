"""校招管控 v2.1 — 样本数据（§9.0 样例人员 + 默认维度/指标/规则/人数目标）。

v2.1 建模：
- 适用范围（bu/position/level，全空=全局）直接挂在规则/目标上。
- 3 个维度（院校标签/专业标签/性别）；性别指标为 男/女。
- 规则：院校/专业为「全局」；性别按「部门」各一套，同适用范围同维度加和 == 100%。
- 人数目标：院校/专业为全局；性别按部门，落在指标层（年度 + 12 月）。
"""
from .constants import DEPTS, SCHOOLS, MAJORS, SEXES  # noqa: F401


def _monthly_from_annual(annual: int) -> list:
    base = annual // 12
    rem = annual % 12
    return [base + 1 if i < rem else base for i in range(12)]


# §9.0 样例人员（31 人，[bu, school, sex, major]，统一 month=8月 / 已入职 / counted）
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
        'code': f'P{_i:03d}',
        'name': f'员工{_i}',
        'bu': _bu,
        'school': _school,
        'sex': _sex,
        'major': _major,
        'month': '8月',
        'status': '已入职',
        'counted': True,
        'position': '',
        'level': '',
    })


# 全局维度默认指标占比（院校/专业，全公司一致）
_SCHOOL_RULES = [
    ('985', 0.34, 0.32, 0.36, '硬约束'),
    ('211', 0.27, 0.20, 0.35, '硬约束'),
    ('双一流', 0.16, 0.10, 0.25, '硬约束'),
    ('其他', 0.23, 0.15, 0.30, '硬约束'),
]
_MAJOR_RULES = [
    ('工学', 0.35, 0.33, 0.40, '软约束'),
    ('其他', 0.65, 0.55, 0.75, '软约束'),
]
# 各方案性别指标占比（男+女 之和 == 100%）
_SEX_RULES = {
    '能电BG': [('男', 0.65, 0.60, 0.70, '硬约束'), ('女', 0.35, 0.20, 0.40, '软约束')],
    '三到BG': [('男', 0.95, 0.90, 1.00, '硬约束'), ('女', 0.05, 0.00, 0.10, '硬约束')],
    '综合BG': [('男', 0.50, 0.40, 0.60, '软约束'), ('女', 0.50, 0.40, 0.60, '软约束')],
    '醒电BG': [('男', 0.70, 0.60, 0.90, '软约束'), ('女', 0.30, 0.10, 0.30, '软约束')],
}

# 各指标年度目标（指标层）；性别按部门近似
_INDICATOR_ANNUAL = {
    '985': 40, '211': 30, '双一流': 20, '其他': 30,
    '工学': 60, '其他': 60,
}
_SEX_ANNUAL = {'男': 70, '女': 50}

DIMENSION_NAMES = ['院校标签', '专业标签', '性别']
INDICATOR_NAMES = {
    '院校标签': SCHOOLS,
    '专业标签': MAJORS,
    '性别': SEXES,
}


def build_rules() -> list:
    """构建全部规则（calc 用 dict 列表，含 bu/position/level）。"""
    rules = []
    for ind, t, lo, hi, st in _SCHOOL_RULES:
        rules.append({'bu': '', 'position': '', 'level': '', 'dimension': '院校标签',
                      'indicator': ind, 'target': t, 'lo': lo, 'hi': hi, 'strength': st})
    for ind, t, lo, hi, st in _MAJOR_RULES:
        rules.append({'bu': '', 'position': '', 'level': '', 'dimension': '专业标签',
                      'indicator': ind, 'target': t, 'lo': lo, 'hi': hi, 'strength': st})
    for bu, sex_rules in _SEX_RULES.items():
        for ind, t, lo, hi, st in sex_rules:
            rules.append({'bu': bu, 'position': '', 'level': '', 'dimension': '性别',
                          'indicator': ind, 'target': t, 'lo': lo, 'hi': hi, 'strength': st})
    return rules


def build_headcounts(year: int = 2026) -> list:
    """构建全部人数目标（calc 用 dict 列表）。"""
    out = []
    for dim, inds in [('院校标签', SCHOOLS), ('专业标签', MAJORS)]:
        for ind in inds:
            annual = _INDICATOR_ANNUAL.get(ind, 0)
            out.append({'bu': '', 'position': '', 'level': '', 'indicator': ind, 'dimension': dim,
                        'year': year, 'annual_target': annual, 'monthly_targets': _monthly_from_annual(annual)})
    for bu in DEPTS:
        for ind in SEXES:
            annual = _SEX_ANNUAL.get(ind, 0)
            out.append({'bu': bu, 'position': '', 'level': '', 'indicator': ind, 'dimension': '性别',
                        'year': year, 'annual_target': annual, 'monthly_targets': _monthly_from_annual(annual)})
    return out
