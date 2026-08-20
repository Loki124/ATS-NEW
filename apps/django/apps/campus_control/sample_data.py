"""校招管控 v2 — 样本数据（§9.0 样例人员 + 默认方案/维度/指标/规则/人数目标）。

供 seed_campus（写库）与 verify_prd（纯函数验收）共用，保证验收与运行时数据一致。

v2 建模：
- 4 个适用范围（各 BG 一套方案）。
- 3 个维度（院校标签/专业标签/性别）；性别指标为 男/女。
- 每方案的每个维度下，指标目标占比之和 == 100%。
- 人数目标落在指标层：每方案每指标每年度 年度目标 + 12 个月目标。
"""
from .constants import DEPTS, SCHOOLS, MAJORS, SEXES, DIMS  # noqa: F401


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


# 各维度默认指标占比（院校/专业 全方案一致）
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

# 各指标年度目标（指标层）；月度 = 年度 / 12 余数摊入前几个月
_INDICATOR_ANNUAL = {
    '985': 40, '211': 30, '双一流': 20, '其他': 30,
    '工学': 60, '其他': 60,
    '男': 70, '女': 50,
}

# 方案定义：方案名 -> {bu, 性别规则}
SCHEME_DEFS = {
    '能电BG校招': {'bu': '能电BG', 'sex': _SEX_RULES['能电BG']},
    '三到BG校招': {'bu': '三到BG', 'sex': _SEX_RULES['三到BG']},
    '综合BG校招': {'bu': '综合BG', 'sex': _SEX_RULES['综合BG']},
    '醒电BG校招': {'bu': '醒电BG', 'sex': _SEX_RULES['醒电BG']},
}

DIMENSION_NAMES = ['院校标签', '专业标签', '性别']
INDICATOR_NAMES = {
    '院校标签': SCHOOLS,
    '专业标签': MAJORS,
    '性别': SEXES,
}


def build_rules(scope_id: str) -> list:
    """构建某方案的规则（calc 用 dict 列表：scope_id/dimension/indicator/target/lo/hi/strength）。"""
    rules = []
    for ind, t, lo, hi, st in _SCHOOL_RULES:
        rules.append({'scope_id': scope_id, 'dimension': '院校标签', 'indicator': ind,
                      'target': t, 'lo': lo, 'hi': hi, 'strength': st})
    for ind, t, lo, hi, st in _MAJOR_RULES:
        rules.append({'scope_id': scope_id, 'dimension': '专业标签', 'indicator': ind,
                      'target': t, 'lo': lo, 'hi': hi, 'strength': st})
    for ind, t, lo, hi, st in SCHEME_DEFS[scope_id]['sex']:
        rules.append({'scope_id': scope_id, 'dimension': '性别', 'indicator': ind,
                      'target': t, 'lo': lo, 'hi': hi, 'strength': st})
    return rules


def build_headcounts(scope_id: str, year: int = 2026) -> list:
    """构建某方案的人数目标（calc 用 dict 列表）。"""
    out = []
    for dim, inds in INDICATOR_NAMES.items():
        for ind in inds:
            annual = _INDICATOR_ANNUAL.get(ind, 0)
            out.append({
                'scope_id': scope_id,
                'indicator': ind,
                'dimension': dim,
                'year': year,
                'annual_target': annual,
                'monthly_targets': _monthly_from_annual(annual),
            })
    return out


def build_scopes() -> list:
    """适用范围（calc 用 dict）。scope_id 用方案名。"""
    return [{'scope_id': name, 'bu': d['bu'], 'position': '', 'level': ''}
            for name, d in SCHEME_DEFS.items()]
