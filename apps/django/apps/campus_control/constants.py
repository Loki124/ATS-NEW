"""人员比例管控系统 — 领域枚举与常量（与 PRD §1 对齐）。"""

# 部门（性别规则的部门轴，也是人数归并轴）
DEPTS = ["能电BG", "三到BG", "综合BG", "醒电BG"]

# 院校标签分组
SCHOOLS = ["985", "211", "双一流", "其他"]

# 专业标签分组
MAJORS = ["工学", "其他"]

# 性别
SEXES = ["男", "女"]

# 招聘月份（样例取值，实际由招聘周期配置）
MONTHS = ["8月", "9月", "10月"]

# 管控维度
DIMS = ["院校标签", "专业标签", "性别"]

# 控制强度
STRENGTH = ["硬约束", "软约束", "仅提示"]

# 人员状态
STATUS = ["已入职", "已Offer", "候选池"]

# group 合法取值集合（依赖 dim）
SCHOOL_GROUPS = SCHOOLS
MAJOR_GROUPS = MAJORS
SEX_GROUPS = [f"{bu}-{sex}" for bu in DEPTS for sex in SEXES]

# dim -> 合法 group 集合（用于 §4.1 校验）
GROUP_CHOICES = {
    "院校标签": SCHOOLS,
    "专业标签": MAJORS,
    "性别": SEX_GROUPS,
}

# 判定结论（录入校验 verdict）
VERDICT_BLOCK = "❌ 阻断提交"
VERDICT_WARN = "⚠️ 允许提交但需关注"
VERDICT_PASS = "✅ 通过"

# 比例状态
RATIO_NORMAL = "正常"
RATIO_BELOW = "低于下限"
RATIO_ABOVE = "高于上限"

# 人数状态
COUNT_MET = "本月达标"
COUNT_GAP = "缺口未达成"
COUNT_UNSET = "未设目标"
