"""校招管控 — 样本数据（§9.0 样例人员 + §2.2/§9 兼容默认规则）。

供 seed_campus（写库）与 verify_prd（纯函数验收）共用，保证验收与运行时数据一致。
"""
from .constants import DEPTS, SCHOOLS, MAJORS, SEXES  # noqa: F401

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
    })

# 默认规则集（§2.2 示例 + §9 断言兼容；确保 §9.1/§9.2 通过）
# 占比以小数存储（0~1）。
DEFAULT_RULES = [
    # 院校标签
    {'dim': '院校标签', 'group': '985', 'target': 0.34, 'lo': 0.32, 'hi': 0.36, 'strength': '硬约束', 'whole': 120, 'month_target': 120},
    {'dim': '院校标签', 'group': '211', 'target': 0.27, 'lo': 0.20, 'hi': 0.35, 'strength': '硬约束', 'whole': 120, 'month_target': 120},
    {'dim': '院校标签', 'group': '双一流', 'target': 0.16, 'lo': 0.10, 'hi': 0.25, 'strength': '硬约束', 'whole': 120, 'month_target': 120},
    {'dim': '院校标签', 'group': '其他', 'target': 0.23, 'lo': 0.15, 'hi': 0.30, 'strength': '硬约束', 'whole': 120, 'month_target': 120},
    # 专业标签（软约束）
    {'dim': '专业标签', 'group': '工学', 'target': 0.35, 'lo': 0.33, 'hi': 0.40, 'strength': '软约束', 'whole': 120, 'month_target': 120},
    {'dim': '专业标签', 'group': '其他', 'target': 0.65, 'lo': 0.55, 'hi': 0.75, 'strength': '软约束', 'whole': 120, 'month_target': 120},
    # 性别（能电BG-男 hi=0.70 硬约束；三到BG-男 hi=1.00 硬约束，§10.1 三到 100% 男）
    {'dim': '性别', 'group': '能电BG-男', 'target': 0.65, 'lo': 0.60, 'hi': 0.70, 'strength': '硬约束', 'whole': 120, 'month_target': 120},
    {'dim': '性别', 'group': '能电BG-女', 'target': 0.30, 'lo': 0.20, 'hi': 0.40, 'strength': '软约束', 'whole': 120, 'month_target': 120},
    {'dim': '性别', 'group': '三到BG-男', 'target': 0.95, 'lo': 0.90, 'hi': 1.00, 'strength': '硬约束', 'whole': 120, 'month_target': 120},
    {'dim': '性别', 'group': '三到BG-女', 'target': 0.05, 'lo': 0.00, 'hi': 0.10, 'strength': '硬约束', 'whole': 120, 'month_target': 120},
    {'dim': '性别', 'group': '综合BG-男', 'target': 0.50, 'lo': 0.40, 'hi': 0.60, 'strength': '软约束', 'whole': 120, 'month_target': 120},
    {'dim': '性别', 'group': '综合BG-女', 'target': 0.50, 'lo': 0.40, 'hi': 0.60, 'strength': '软约束', 'whole': 120, 'month_target': 120},
    {'dim': '性别', 'group': '醒电BG-男', 'target': 0.70, 'lo': 0.60, 'hi': 0.90, 'strength': '软约束', 'whole': 120, 'month_target': 120},
    {'dim': '性别', 'group': '醒电BG-女', 'target': 0.30, 'lo': 0.10, 'hi': 0.30, 'strength': '软约束', 'whole': 120, 'month_target': 120},
]
