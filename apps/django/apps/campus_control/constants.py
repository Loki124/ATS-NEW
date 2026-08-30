"""人员比例管控系统 — 领域枚举与常量（v2：适用范围 + 维度/指标建模）。

v2 变更：
- 新增 POSITIONS（职务）/ LEVELS（职级）枚举，用于「适用范围」配置。
- 维度/指标改为动态建模：维度为院校标签/专业标签/性别；指标为其下分类
  （院校→SCHOOLS、专业→MAJORS、性别→SEXES 男/女），由 ControlIndicator 落库维护。
- 月份工具：招聘月份 "8月" ↔ 日历月序号 1~12。
"""

# 部门（性别规则的部门轴，也是人数归并轴；v2 作为适用范围 BG 部门）
DEPTS = ["能电BG", "三到BG", "综合BG", "醒电BG"]

# 院校标签指标
SCHOOLS = ["985", "211", "双一流", "其他"]

# 专业标签指标
MAJORS = ["工学", "其他"]

# 性别指标（v2：性别维度只含 男/女，分母按适用范围所属部门）
SEXES = ["男", "女"]

# 招聘月份（样例取值，实际由招聘周期配置）
MONTHS = ["8月", "9月", "10月"]

# 管控维度
DIMS = ["院校标签", "专业标签", "性别"]

# 控制强度（v2.9：合并软约束与仅提示，后端处理完全一致——放行+提示；UI 收敛到两档）
STRENGTH = ["硬约束", "软约束"]

# 人员状态（v2.5 核心术语对齐）
# 在途Offer：offer 阶段除未创建外的所有状态（含已创建审批未创建）
# 在途待入职：候选人处于待入职阶段
# 在职：已正式入职员工
# 候选池：尚未进入 offer/入职流程
STATUS = ["在职", "在途Offer", "在途待入职", "候选池"]

# 适用范围 —— 职务 / 职级（可空表示「不限」，由前端下拉提供，后端仅作过滤）
POSITIONS = ["技术研发", "产品", "设计", "运营", "职能", "销售"]
LEVELS = ["L1", "L2", "L3", "L4", "L5"]

# 维度 -> 默认指标集合（用于种子初始化；线上以 ControlIndicator 落库为准）
DIMENSION_INDICATORS = {
    "院校标签": SCHOOLS,
    "专业标签": MAJORS,
    "性别": SEXES,
}

# group 合法取值集合（依赖 dim，向后兼容旧逻辑/测试）
SCHOOL_GROUPS = SCHOOLS
MAJOR_GROUPS = MAJORS
SEX_GROUPS = [f"{bu}-{sex}" for bu in DEPTS for sex in SEXES]

# dim -> 合法 group 集合（用于 §4.1 校验 / 旧路径）
GROUP_CHOICES = {
    "院校标签": SCHOOLS,
    "专业标签": MAJORS,
    "性别": SEX_GROUPS,
}

# 判定结论（录入校验 verdict）
VERDICT_BLOCK = "❌ 阻断提交"
VERDICT_WARN = "⚠️ 允许提交但需关注"
VERDICT_PASS = "✅ 通过"
VERDICT_LEVEL = {VERDICT_BLOCK: "block", VERDICT_WARN: "warn", VERDICT_PASS: "pass"}

# 比例状态
RATIO_NORMAL = "正常"
RATIO_BELOW = "低于下限"
RATIO_ABOVE = "高于上限"

# 人数状态
COUNT_MET = "本月达标"
COUNT_GAP = "缺口未达成"
COUNT_UNSET = "未设目标"

# 100% 加和校验结论
SUM_OK = "ok"
SUM_BELOW = "below"
SUM_ABOVE = "above"


def month_to_index(month: str) -> int:
    """招聘月份 "8月" -> 日历月序号 8（非法返回 0）。"""
    if not month:
        return 0
    s = str(month).replace("月", "").strip()
    try:
        return int(s)
    except ValueError:
        return 0


def month_label(idx: int) -> str:
    """日历月序号 8 -> "8月"。"""
    return f"{int(idx)}月"


# 12 个日历月标签（1月..12月）
ALL_MONTHS = [month_label(i) for i in range(1, 13)]
