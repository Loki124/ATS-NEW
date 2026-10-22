"""校招管控 v2.4 — 样本数据（§9.0 样例人员 + 默认维度/指标/规则[含人数目标]）。

v2.4 建模：
- 适用范围（bu/position/level，全空=全局）直接挂在规则上。
- 3 个维度（院校标签/专业标签/性别）；性别指标为 男/女。
- 规则：院校/专业为「全局」；性别按「部门」各一套，同(适用范围,年度)同维度加和 == 100%。
- 人数目标（年度 + 12 月）直接承载于规则上（指标层）。

2026-10-21（二期）数据真实化：
- 姓名由「员工N」改为真实姓名（与性别一致），并保留 `legacy_name` 记录改名前的老姓名，
  供 seed 命令**原地更新**存量行（改名 + 补字段），避免重复行、不删任何数据。
- 在职人员补 8 位工号（YYMM + 4 位序号）与实际入职日期（8 月入职，核算月份口径不变）。
- 补齐院校名称 / 学历 / 联系电话，供「个人档案」详情页呈现。
"""
from datetime import date

from .constants import DEPTS, MAJORS, SCHOOLS, SEXES  # noqa: F401


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

# 真实姓名（与 _SAMPLE 顺序一一对应，性别与 _SAMPLE 的 sex 一致）
_SAMPLE_NAMES = [
    "王明远", "李泽宇", "张思齐", "刘浩然", "陈睿泽", "杨文博", "赵一鸣", "黄嘉豪", "周天佑",
    "吴思彤", "徐雨桐", "孙梦琪",
    "马若飞", "朱承宇", "胡志远", "郭锦程", "何修远", "高立诚",
    "林昊天", "罗宇轩", "郑逸凡", "梁晨曦",
    "宋若曦", "唐佳怡", "许欣然", "邓语嫣",
    "冯昱辰", "曾皓宇", "彭思睿",
    "蔡可欣",
    "蒋宏毅",
]

# 院校标签 → 真实校名池（档案详情「院校名称」用；院校标签本身仍用于管控计算）
SCHOOL_NAME_POOL = {
    "985": ["华中科技大学", "武汉大学", "西安交通大学", "哈尔滨工业大学", "东南大学", "同济大学", "浙江大学"],
    "211": ["武汉理工大学", "南京邮电大学", "苏州大学", "暨南大学", "南京师范大学", "合肥工业大学"],
    "双一流": ["南方科技大学", "南京信息工程大学", "宁波大学"],
    "其他": ["湖北工业大学", "江苏科技大学", "安徽工业大学"],
}

# 学历分布（多数本科，少量硕博）
EDUCATION_POOL = ["本科", "本科", "硕士", "本科", "博士"]


def derive_realistic_fields(index: int, school: str) -> dict:
    """按序号确定性派生「院校名称 / 学历 / 联系电话」。

    同一 index 每次得到相同结果 ⇒ seed 幂等（重复执行不会让数据漂移）。
    """
    pool = SCHOOL_NAME_POOL.get(school) or SCHOOL_NAME_POOL["其他"]
    return {
        "school_name": pool[index % len(pool)],
        "education": EDUCATION_POOL[index % len(EDUCATION_POOL)],
        "phone": f"158{10000000 + (index * 137317) % 89999999:08d}",
    }


SAMPLE_PERSONS = []
for _i, (_bu, _school, _sex, _major) in enumerate(_SAMPLE, 1):
    _idx = _i - 1
    SAMPLE_PERSONS.append({
        # 'code' 不再硬编码 —— 由 Person.save() 自动补号 C+8 流水号（连续且唯一）。
        'name': _SAMPLE_NAMES[_idx],
        # 改名前的老姓名（存量行靠它原地更新，不新建重复行）
        'legacy_name': f'员工{_i}',
        'bu': _bu,
        'school': _school,
        'sex': _sex,
        'major': _major,
        'month': '8月',
        'status': '在职',
        'counted': True,
        'position': '',
        'level': '',
        # 在职 → 已补 8 位工号 + 实际入职日期（8 月入职，计入 8 月核算口径不变）
        'employee_id': f'2508{_i:04d}',
        'actual_entry_date': date(2025, 8, 4 + _idx % 24),
        **derive_realistic_fields(_idx, _school),
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
