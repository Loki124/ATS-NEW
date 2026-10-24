"""校招生考核域模型（campus_assessment app）。

十张表（契约 §2.1 逐条对齐，字段名 / db_table / choices 一律照抄，不自行发挥）：

| 模型 | db_table | 用途 |
|---|---|---|
| AssessmentTemplate | campus_assessment_templates | 考核模板（适用部门/班级 + 绑定轮岗阶段 + 周期类型） |
| AssessmentTemplateItem | campus_assessment_template_items | 模板维度（权重 + 目标要求） |
| MonthlyAssessment | campus_monthly_assessments | 月度考核（KPI / 考试 / 加减分 / 总分） |
| FiveForceScore | campus_five_force_scores | 五行五力（学习力/执行力/协作力/创新力/抗压适应力） |
| AttendanceRecord | campus_attendance_records | 每日打卡 |
| AttendanceMonthly | campus_attendance_monthly | 月度考勤汇总 |
| FeedbackRecord | campus_feedback_records | 反馈 / 异常记录 |
| MonthlyReport | campus_monthly_reports | 月报 |
| MonthlyReportScore | campus_monthly_report_scores | 月报评分明细（业务 / 成长两个角色） |
| Probation | campus_probations | 试用期考核 |

口径来源（写码时逐条对照）：
- 结构：docs/02-architecture/ARCH_校招生全生命周期移植_技术契约_2026-10-23.md §2.1
- 视图与算法：docs/03-product/校招生管理_逆向功能清单与差距矩阵_2026-10-23.md
  §4.3（考核视图）与 §5（算法 A1~A9）

跨 app 引用纪律（契约 §1.1）：
- 人员一律用**字符串外键** `'campus_control.Person'` —— 不 import models，
  避免与 campus_control / campus_learning / campus_placement 互相成环；
- 用户引用 `'core.User'`。

统一基类 `FullAuditModel, UUIDModel`：时间戳 + 软删（deleted_at）+ 创建人 + nanoid 主键。
DELETE 走软删，不硬删；列表默认过滤 `deleted_at__isnull=True`。
"""
from django.db import models

from apps.common.models import FullAuditModel, UUIDModel
from apps.core.models import User


class AssessmentTemplate(FullAuditModel, UUIDModel):
    """考核模板（逆向清单 §4.3「考核模板」页签）。

    多套模板，各自适用**部门 / 班级 / 全部**，绑定**轮岗阶段**
    （第1/2/3阶段、定岗后）与**周期类型**（阶段末考核 / 月度考核）。
    维度权重与目标要求挂在子表 `AssessmentTemplateItem`（related_name='items'）。

    ⚠️ 权重合计 ≠ 100% 的黄色告警属**前端展示层**职责（逆向清单 §4.3），
    后端只保证 weight 是正整数百分比，不做硬拦（避免运营改模板时被卡死）。
    """

    class ScopeType(models.TextChoices):
        ALL = 'all', '全部'
        DEPT = 'dept', '部门'
        CLASS = 'class', '班级'

    class Stage(models.TextChoices):
        POST = 'post', '定岗后'
        STAGE1 = 'stage1', '第1阶段'
        STAGE2 = 'stage2', '第2阶段'
        STAGE3 = 'stage3', '第3阶段'

    class PeriodType(models.TextChoices):
        STAGE = 'stage', '阶段末考核'
        MONTHLY = 'monthly', '月度考核'

    name = models.CharField(max_length=64, verbose_name='模板名称')
    scope_type = models.CharField(
        max_length=16, choices=ScopeType.choices, default=ScopeType.ALL,
        db_index=True, verbose_name='适用范围类型',
    )
    scope_values = models.JSONField(
        default=list, blank=True,
        help_text='适用范围取值列表：scope_type=dept 存部门、=class 存班级编码；all 时为空',
    )
    stage = models.CharField(
        max_length=16, choices=Stage.choices, default=Stage.STAGE1,
        db_index=True, verbose_name='绑定轮岗阶段',
    )
    period_type = models.CharField(
        max_length=16, choices=PeriodType.choices, default=PeriodType.MONTHLY,
        verbose_name='周期类型',
    )
    enabled = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    class Meta:
        db_table = 'campus_assessment_templates'
        verbose_name = '考核模板'
        verbose_name_plural = '考核模板'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}({self.get_scope_type_display()})'


class AssessmentTemplateItem(FullAuditModel, UUIDModel):
    """考核模板维度（模板 → 维度，权重 + 目标要求）。

    `weight` 是**百分比**（契约 §2.1 标注 weight PositiveInt(%)），
    例如 30 表示 30%；`target` 是该维度的目标要求文本。
    """

    template = models.ForeignKey(
        AssessmentTemplate, on_delete=models.CASCADE,
        related_name='items', verbose_name='考核模板',
    )
    name = models.CharField(max_length=64, verbose_name='维度名称')
    weight = models.PositiveIntegerField(
        default=0, verbose_name='权重(%)',
        help_text='权重百分比，整数；合计 100% 为标准配比',
    )
    target = models.CharField(max_length=255, blank=True, default='', verbose_name='目标要求')

    class Meta:
        db_table = 'campus_assessment_template_items'
        verbose_name = '模板维度'
        verbose_name_plural = '模板维度'
        ordering = ['id']

    def __str__(self):
        return f'{self.name}({self.weight}%)'


class MonthlyAssessment(FullAuditModel, UUIDModel):
    """月度考核（逆向清单 §4.3「月度数据」页签）。

    列：校招生 / 班级 / 部门 / KPI / 考试 / 加减分 / 总分 / 状态（已核对 / 待核对）。

    🔴 **状态机口径**：只有 `status='checked'`（已核对）的记录**计入排名**
    （逆向清单 §4.3 原文：「核对通过（锁定当月并计入排名）」）。
    `check` 动作即做两件事：置 checked + 写 checked_by/checked_at + **锁定**该月
    （此后不可再改 KPI/考试/加减分）。

    总分不在本表落库 —— 由公式实时算：
    `totalScore = round(KPI×0.6 + 考试×0.4) + 加减分`（逆向清单 A1 / core.js:255）。
    单测锁死该公式，见 tests/test_ranking.py。
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', '待核对'
        CHECKED = 'checked', '已核对'

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='monthly_assessments', verbose_name='校招生',
    )
    ym = models.CharField(max_length=7, db_index=True, verbose_name='考核月份',
                          help_text='YYYY-MM')
    kpi = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='KPI 得分')
    exam = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='考试得分')
    adjust = models.IntegerField(default=0, verbose_name='加减分',
                                 help_text='历月加减分累计值，可为负（迟到 −1）')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT,
        db_index=True, verbose_name='状态',
    )
    note = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    checked_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='核对人',
    )
    checked_at = models.DateTimeField(null=True, blank=True, verbose_name='核对时间')

    class Meta:
        db_table = 'campus_monthly_assessments'
        verbose_name = '月度考核'
        verbose_name_plural = '月度考核'
        ordering = ['-ym', 'id']

    def __str__(self):
        return f'{self.person_id}·{self.ym}({self.status})'


class FiveForceScore(FullAuditModel, UUIDModel):
    """五行五力（逆向清单 A5 / data.js:897）。

    五个维度中文名固定：学习力 / 执行力 / 协作力 / 创新力 / 抗压适应力。

    `dimForce = round(5 个维度分值的算术平均)`（逆向清单 A5 / views2.js:82）。
    同一人多次打分时取**最近一次**（scored_at 最新）—— 契约未定义多次评分口径，
    取最新是最贴近「当前能力评估」语义的选择，已在交付说明中标注。
    """

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='five_force_scores', verbose_name='校招生',
    )
    learning = models.PositiveIntegerField(default=0, verbose_name='学习力')
    execution = models.PositiveIntegerField(default=0, verbose_name='执行力')
    collaboration = models.PositiveIntegerField(default=0, verbose_name='协作力')
    innovation = models.PositiveIntegerField(default=0, verbose_name='创新力')
    resilience = models.PositiveIntegerField(default=0, verbose_name='抗压适应力')
    scored_at = models.DateField(verbose_name='评分日期')
    scorer = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='评分人',
    )

    class Meta:
        db_table = 'campus_five_force_scores'
        verbose_name = '五行五力'
        verbose_name_plural = '五行五力'
        ordering = ['-scored_at', 'id']

    def __str__(self):
        return f'{self.person_id}·{self.scored_at}'

    @property
    def dimension_values(self):
        """五个维度的取值序列（顺序固定：学习力/执行力/协作力/创新力/抗压适应力）。"""
        return [
            self.learning, self.execution, self.collaboration,
            self.innovation, self.resilience,
        ]


class AttendanceRecord(FullAuditModel, UUIDModel):
    """每日打卡（逆向清单 §4.3「考勤管理」）。

    status 取值：正常 / 迟到 / 请假 / 缺勤 / 加班（契约 §2.1 明确给中文枚举）。
    """

    class Status(models.TextChoices):
        NORMAL = '正常', '正常'
        LATE = '迟到', '迟到'
        LEAVE = '请假', '请假'
        ABSENT = '缺勤', '缺勤'
        OVERTIME = '加班', '加班'

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='attendance_records', verbose_name='校招生',
    )
    date = models.DateField(db_index=True, verbose_name='打卡日期')
    punch_time = models.TimeField(null=True, blank=True, verbose_name='打卡时间')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.NORMAL,
        db_index=True, verbose_name='当日状态',
    )
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_attendance_records'
        verbose_name = '每日打卡'
        verbose_name_plural = '每日打卡'
        ordering = ['-date', 'punch_time', 'id']

    def __str__(self):
        return f'{self.person_id}·{self.date}({self.status})'


class AttendanceMonthly(FullAuditModel, UUIDModel):
    """月度考勤汇总（逆向清单 §4.2「考勤管理」页签 + A9 考勤维度）。

    考勤维度值（逆向清单 A9 / views2.js:141）：
        `round(Σ(出勤 − 迟到×0.5) / 月数, 1)`

    ⚠️ 契约 §2.1 未给 `status` 的 choices —— 本表状态沿用**每日打卡的同一套词表**
    （正常/迟到/请假/缺勤），避免同一视图出现两套词表；已在校验说明中标注为偏差。
    """

    class Status(models.TextChoices):
        NORMAL = '正常', '正常'
        LATE = '迟到', '迟到'
        LEAVE = '请假', '请假'
        ABSENT = '缺勤', '缺勤'

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='attendance_monthly', verbose_name='校招生',
    )
    ym = models.CharField(max_length=7, db_index=True, verbose_name='考勤月份',
                          help_text='YYYY-MM')
    attend_days = models.PositiveIntegerField(default=0, verbose_name='出勤天数')
    late_count = models.PositiveIntegerField(default=0, verbose_name='迟到次数')
    leave_days = models.PositiveIntegerField(default=0, verbose_name='请假天数')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.NORMAL,
        verbose_name='月度状态',
    )

    class Meta:
        db_table = 'campus_attendance_monthly'
        verbose_name = '月度考勤汇总'
        verbose_name_plural = '月度考勤汇总'
        ordering = ['-ym', 'id']

    def __str__(self):
        return f'{self.person_id}·{self.ym}'


class FeedbackRecord(FullAuditModel, UUIDModel):
    """反馈 / 异常记录（逆向清单 §4.3「反馈记录」页签）。

    两类：
    - category='issue' → 问题·情况记录（逆向数据源 `exceptions` 集合，49 条）
    - category='mentor' → 导师带教反馈

    状态机（逆向清单 §4.3）：`处理中` → `已解决` / `已闭环`。
    办结动作 `resolve` 落 `status='已解决'` + `handler` + `handled_at`。

    `attachments` 存证据附件描述列表（JSON list）；非空即「含证据记录」。
    """

    class Category(models.TextChoices):
        ISSUE = 'issue', '问题·情况记录'
        MENTOR = 'mentor', '导师带教反馈'

    class Status(models.TextChoices):
        PROCESSING = '处理中', '处理中'
        RESOLVED = '已解决', '已解决'
        CLOSED = '已闭环', '已闭环'

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='feedback_records', verbose_name='校招生',
    )
    date = models.DateField(db_index=True, verbose_name='记录日期')
    reporter = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='记录人',
    )
    category = models.CharField(
        max_length=16, choices=Category.choices, default=Category.ISSUE,
        db_index=True, verbose_name='记录分类',
    )
    type = models.CharField(max_length=32, blank=True, default='', verbose_name='类型')
    content = models.TextField(blank=True, default='', verbose_name='问题描述')
    handling = models.TextField(blank=True, default='', verbose_name='处理方式')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PROCESSING,
        db_index=True, verbose_name='处理状态',
    )
    attachments = models.JSONField(default=list, blank=True, verbose_name='证据附件')
    handler = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='处理人',
    )
    handled_at = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')

    class Meta:
        db_table = 'campus_feedback_records'
        verbose_name = '反馈记录'
        verbose_name_plural = '反馈记录'
        ordering = ['-date', 'id']

    def __str__(self):
        return f'{self.person_id}·{self.date}({self.status})'


class MonthlyReport(FullAuditModel, UUIDModel):
    """月报（逆向清单 §4.2「月报提交 / 月报评分」，算法 A7）。

    状态机：`draft` → `submitted`（提交）→ `scored`（评分动作落库即置）。

    🔴 **final_score 的回算口径**（逆向清单 A7 / core.js:258）：
        `final_score = round(business.total×0.7 + growth.total×0.3, 1)`
        其中每个 total = case + insight + problem + clarity + executable 五子项之和。
    另一角色未评时，`final_score` 按**已有侧**计算，未评侧为 None；
    不再等待另一角色补齐才置 `scored`（具体评分口径以 views.score 为准）。
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        SUBMITTED = 'submitted', '已提交'
        SCORED = 'scored', '已评分'

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='monthly_reports', verbose_name='校招生',
    )
    ym = models.CharField(max_length=7, db_index=True, verbose_name='月报月份',
                          help_text='YYYY-MM')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='提交时间')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT,
        db_index=True, verbose_name='状态',
    )
    business_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, verbose_name='业务导师得分',
    )
    growth_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, verbose_name='成长导师得分',
    )
    final_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, verbose_name='综合得分',
        help_text='round(业务总分×0.7 + 成长总分×0.3, 1)',
    )
    comment = models.TextField(blank=True, default='', verbose_name='评语')

    class Meta:
        db_table = 'campus_monthly_reports'
        verbose_name = '月报'
        verbose_name_plural = '月报'
        ordering = ['-ym', 'id']

    def __str__(self):
        return f'{self.person_id}·{self.ym}({self.status})'


class MonthlyReportScore(FullAuditModel, UUIDModel):
    """月报评分明细（业务导师 / 成长导师两个角色各一条）。

    五个子项：case（案例）/ insight（洞察）/ problem（问题分析）/
    clarity（表达清晰）/ executable（可执行性）——
    总分 = 五子项之和（逆向清单 A7：「各总分 = 5 子项之和」）。
    """

    class Role(models.TextChoices):
        BUSINESS = 'business', '业务导师'
        GROWTH = 'growth', '成长导师'

    report = models.ForeignKey(
        MonthlyReport, on_delete=models.CASCADE,
        related_name='scores', verbose_name='月报',
    )
    role = models.CharField(
        max_length=16, choices=Role.choices, db_index=True, verbose_name='评分角色',
    )
    case = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='案例')
    insight = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='洞察')
    problem = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='问题分析')
    clarity = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='表达清晰')
    executable = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name='可执行性',
    )
    total = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, verbose_name='角色总分',
        help_text='五子项之和',
    )
    scorer = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='评分人',
    )
    comment = models.TextField(blank=True, default='', verbose_name='评语')
    scored_at = models.DateTimeField(null=True, blank=True, verbose_name='评分时间')

    class Meta:
        db_table = 'campus_monthly_report_scores'
        verbose_name = '月报评分明细'
        verbose_name_plural = '月报评分明细'
        ordering = ['role', 'id']
        unique_together = [('report', 'role')]

    def __str__(self):
        return f'{self.report_id}·{self.role}({self.total})'


class Probation(FullAuditModel, UUIDModel):
    """试用期考核（逆向清单 §4.3「试用期考核」页签）。

    两部分：① 轮岗阶段考核（`rotation_result` 轮岗评分 / `rotation_level` 轮岗等级）
    ② 定岗 3 个月考核（`p3m_kpi` 定岗 3 月 KPI / `p3m_competency` 定岗 3 月能力评价）。

    处理类型（决策）：转正 / 延期转正 / 不合格。
    """

    class Decision(models.TextChoices):
        CONFIRM = '转正', '转正'
        DELAY = '延期转正', '延期转正'
        REJECT = '不合格', '不合格'

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='probations', verbose_name='校招生',
    )
    rotation_result = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, verbose_name='轮岗评分',
    )
    rotation_level = models.CharField(
        max_length=16, blank=True, default='', verbose_name='轮岗等级',
    )
    p3m_kpi = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='定岗3月KPI',
    )
    p3m_competency = models.CharField(
        max_length=32, blank=True, default='', verbose_name='定岗3月能力评价',
    )
    decision = models.CharField(
        max_length=16, choices=Decision.choices, blank=True, default='',
        db_index=True, verbose_name='处理类型',
    )
    decided_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='决策人',
    )
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name='决策时间')
    decision_note = models.TextField(blank=True, default='', verbose_name='决策说明')

    class Meta:
        db_table = 'campus_probations'
        verbose_name = '试用期考核'
        verbose_name_plural = '试用期考核'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.person_id}({self.decision or "未决策"})'
