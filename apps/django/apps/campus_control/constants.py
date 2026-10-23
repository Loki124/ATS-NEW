"""人员比例管控系统 — 领域枚举与常量（v2：适用范围 + 维度/指标建模）。

v2 变更：
- 新增 POSITIONS（职务）/ LEVELS（职级）枚举，用于「适用范围」配置。
- 维度/指标改为动态建模：维度为院校标签/专业标签/性别；指标为其下分类
  （院校→SCHOOLS、专业→MAJORS、性别→SEXES 男/女），由 ControlIndicator 落库维护。
- 月份工具：招聘月份 "8月" ↔ 日历月序号 1~12。
"""

# 部门（性别规则的部门轴，也是人数归并轴；v2 作为适用范围 BG 部门）
# 2026-10-23（校招生全生命周期移植 · 真实数据导入）：按《校招生轮岗管理.xlsx》
#   的真实 BG 分布补齐 —— 原 4 档缺「能人BG / 能智BG / 能本BG」三个真实存在的 BG，
#   而源数据 878 人里有 139 人落在这三个 BG。若强行归入「综合BG」= **事实错误**
#   （管控页按 BG 统计人数时会把这 139 人算进综合BG，口径直接失真）。
#   → 按源数据补齐为 7 档（原 4 档保持不变，新增 3 档追加在后，**不改动既有顺序**，
#     以免影响按 DEPTS 顺序取「最优」的存量逻辑）。
#   ⚠️ 新增 BG 暂无对应管控规则（ControlRule.bu 为空 = 全局规则），全局规则的样本量
#     会因导入 878 名历史校招生而变化 —— 这是导入本身的必然结果，已在导入摘要与
#     交付文档中如实登记。
DEPTS = ["能电BG", "三到BG", "综合BG", "醒电BG", "能人BG", "能智BG", "能本BG"]

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
# 2026-10-21 兵哥口径收敛为三态：**在职 / 待入职 / 离职**
#   - 在职：已正式入职员工
#   - 待入职：候选人尚未入职（原「在途Offer」「在途待入职」「候选池」三态合并 —— 均属「未入职」，
#     在人员管理里不再区分；存量数据由迁移 0016 统一改写为「待入职」）
#   - 离职：已入职后离职；不计入占编核算
#     （核算口径见 calc._COUNTED_STATUSES，该集合不含「离职」，无需额外排除逻辑）
STATUS = ["在职", "待入职", "离职"]

# 2026-10-21 兵哥口径：工号 / 入职日期 / 预计入职日期 三个字段的形态随在职状态走。
#   未入职（待入职）：无工号、无入职日期，有预计入职日期
#   已入职（在职/离职）：有工号、有入职日期、有预计入职日期
# 口径落点：序列化器 PersonSerializer.validate（唯一写入口，模型层不重复校验）。
PENDING_STATUSES = ["待入职"]
EMPLOYED_STATUSES = ["在职", "离职"]

# 工号格式：8 位纯数字（与存量 36 条在职数据兼容：25080001 …）
EMPLOYEE_ID_PATTERN = r'^\d{8}$'

# 学历（2026-10-21 二期新增：档案详情「基本信息」字段）
# 取值与 apps/dictionary 种子 EDUCATION（高中及以下/中专中技/大专/本科/硕士/博士/其他）对齐；
# 仍按 school/sex/major 同口径硬编码于本文件（G-09 动态维度化 TODO 不含本项）。
EDUCATIONS = ["博士", "硕士", "本科", "大专", "中专/中技", "高中及以下", "其他"]

# 学位（2026-10-22：编辑弹窗「毕业院校」组新增「学位」，与学历分列）
#   学历 = 培养层次（本科/硕士/…）；学位 = 授予的学位（学士/硕士/博士/…）。
DEGREES = ["学士", "硕士", "博士", "其他"]

# 适用范围 —— 职务 / 职级（可空表示「不限」，由前端下拉提供，后端仅作过滤）
POSITIONS = ["技术研发", "产品", "设计", "运营", "职能", "销售"]
LEVELS = ["L1", "L2", "L3", "L4", "L5"]

# 人员管理（校招生档案）的取数范围：**26 年及以后入职或预计入职**的数据。
#
# 需求来源：聂荣《校招生管理系统 - 需求文档》（2026-10-23）· 人员管理模块 · 取数规则
#   「数据范围（26年及以后入职或预计入职数据）」
#
# ⚠️ 「无入职日期 / 无预计入职日期」的人员**不被排除**：无从判定归属年份，
#    宁留勿删（档案刚由招聘系统认领时两个日期都还没有）。
# ⚠️ 需要看全部历史数据时用 `?entry_scope=all` 显式关掉该过滤（编制管控等旁路不受影响）。
DATA_SCOPE_ENTRY_YEAR_MIN = 2026

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
