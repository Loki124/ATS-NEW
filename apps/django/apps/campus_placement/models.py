"""校招定岗与结算域模型（campus_placement app）。

契约：`docs/02-architecture/ARCH_校招生全生命周期移植_技术契约_2026-10-23.md` §4.1
逆向依据：`docs/03-product/校招生管理_逆向功能清单与差距矩阵_2026-10-23.md` §4.3（六步撮合状态机）/ §4.4（定岗安排 / 交易结算）

统一基类 `FullAuditModel`（时间戳 + 软删 deleted_at + 创建人/最后修改人）+ `UUIDModel`（nanoid 21 位主键）。
人员一律外键引用 `campus_control.Person`（**不建第二套人员主数据**）。

⚠️ **双选撮合六步状态机**（逆向清单 §4.3，本文件是它的字段载体）：
    ① 校招生填报 N 个志愿（N = 该批次 `SelectionFlow.wish_limit`，缺省继承全局默认 2）
    ② 撮合启动后：第一志愿推送至「岗位所属业务 BP」
    ③ BP 录取 → 后续志愿自动释放（status=已释放）；BP 放弃 → 下一志愿自动推送
    ④ 两志愿均未被选 → 进入人才市场（status=人才市场），全员 BP 可选
    ⑤ 仍未被选 → 班主任/管理员指定分配（channel=指定）
    ⑥ 管理员发布双选结果
状态流转的具体编排（推送 / 录取释放 / 放弃顺延 / 人才市场 / 指定分配）在 `views.py`。
"""
from decimal import Decimal

from django.db import models

from apps.common.models import FullAuditModel, UUIDModel

#: 全局默认志愿数（逆向清单 §4.3 ①：「默认 2，可按批次覆盖」）
DEFAULT_WISH_LIMIT = 2


class PositionDemand(FullAuditModel, UUIDModel):
    """岗位需求（逆向清单 §4.3「岗位池 / 需求审核」）。

    **审核流**（逆向清单原文）：「待审核 → 已通过 / 已驳回，HRBP 可提交/编辑/撤回需求申请，
    管理员审核发布并控制开放窗口」→ 故 `need_status` 四态：
    待审核 → 已通过 → 已发布；已驳回为终态（可重新提交回待审核）。

    **岗位开放判定顺序**（逆向清单 §4.3，顺序固定，不得调整）：
        审核状态 → 开放开关 → 发布范围(all/batch/intentDept) → 面向届数/班级 → 窗口期
    实现见 `views.py` 的 `_position_open_state()`。
    """

    class NeedStatus(models.TextChoices):
        PENDING = '待审核', '待审核'
        APPROVED = '已通过', '已通过'
        REJECTED = '已驳回', '已驳回'
        PUBLISHED = '已发布', '已发布'

    class ScopeType(models.TextChoices):
        """发布范围三档（逆向清单 §4.3）。"""

        ALL = 'all', '全部'
        BATCH = 'batch', '按批次'
        INTENT_DEPT = 'intentDept', '按意向部门'

    name = models.CharField(max_length=128, verbose_name='岗位名称')
    dept = models.CharField(max_length=64, blank=True, default='', verbose_name='用人部门')
    business_dept = models.CharField(max_length=64, blank=True, default='', verbose_name='业务部门')
    headcount = models.PositiveIntegerField(default=1, verbose_name='需求人数')
    submitter = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='提交人',
    )
    need_status = models.CharField(
        max_length=16, choices=NeedStatus.choices, default=NeedStatus.PENDING,
        verbose_name='需求状态', db_index=True,
    )
    need_desc = models.TextField(blank=True, default='', verbose_name='需求描述')
    biz_intro = models.TextField(blank=True, default='', verbose_name='业务介绍')
    dept_intro = models.TextField(blank=True, default='', verbose_name='部门介绍')
    assess_req = models.TextField(blank=True, default='', verbose_name='考核要求')
    need_time = models.CharField(max_length=64, blank=True, default='', verbose_name='需求时间')
    work_location = models.CharField(max_length=64, blank=True, default='', verbose_name='工作地点')
    bp = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='负责BP',
    )
    scope_type = models.CharField(
        max_length=16, choices=ScopeType.choices, default=ScopeType.ALL,
        verbose_name='发布范围',
    )
    scope_batch = models.CharField(max_length=32, blank=True, default='', verbose_name='发布范围批次')
    scope_intent_depts = models.JSONField(default=list, verbose_name='发布范围部门列表')
    open_enabled = models.BooleanField(default=False, verbose_name='开放报名')
    open_start = models.DateField(null=True, blank=True, verbose_name='开放开始日')
    open_end = models.DateField(null=True, blank=True, verbose_name='开放结束日')
    open_batch_no = models.CharField(max_length=32, blank=True, default='', verbose_name='面向批次号')

    class Meta:
        db_table = 'campus_position_demands'
        verbose_name = '岗位需求'
        verbose_name_plural = '岗位需求'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}·{self.need_status}'


class PositionApplication(FullAuditModel, UUIDModel):
    """志愿（逆向清单 §4.3「志愿推送 / 人才市场」）。

    `order` = 第几志愿（1 / 2 …，上限 = 该批次 wish_limit）。
    `channel` = 志愿（学生自填）/ 指定（班主任·管理员指定分配，见状态机 ⑤）。
    `status` 六态（契约 §4.1）：
        已填报 → 推送中 → 已录取 / 已放弃 / 已释放；两志愿均未被选 → 人才市场。
    """

    class Channel(models.TextChoices):
        WISH = '志愿', '志愿'
        ASSIGNED = '指定', '指定'

    class Status(models.TextChoices):
        FILED = '已填报', '已填报'
        PUSHING = '推送中', '推送中'
        ACCEPTED = '已录取', '已录取'
        REJECTED = '已放弃', '已放弃'
        RELEASED = '已释放', '已释放'
        MARKET = '人才市场', '人才市场'

    class Decision(models.TextChoices):
        """BP 对志愿的决定（契约 §4.1 `decision` Char(16) choices(接受/拒绝, 空)）。

        枚举而非裸字符串：裸 CharField 不校验取值，任意字符串都能入库，
        下游读 `decision` 时只能靠字符串比对，脏值会静默穿透。
        空值（''）仍合法 —— Django `Field.validate` 对 `empty_values` 短路，
        且 `blank=True` 允许未决定态。
        """

        ACCEPT = '接受', '接受'
        REJECT = '拒绝', '拒绝'

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='position_applications', verbose_name='校招生',
    )
    position = models.ForeignKey(
        PositionDemand, on_delete=models.CASCADE,
        related_name='applications', verbose_name='岗位需求',
    )
    order = models.PositiveIntegerField(default=1, verbose_name='志愿顺序')
    channel = models.CharField(
        max_length=16, choices=Channel.choices, default=Channel.WISH, verbose_name='来源渠道',
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.FILED,
        verbose_name='状态', db_index=True,
    )
    pushed_at = models.DateTimeField(null=True, blank=True, verbose_name='推送时间')
    pushed_by = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='推送人',
    )
    decision = models.CharField(
        max_length=16, choices=Decision.choices, blank=True, default='', verbose_name='BP决定',
    )
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name='决定时间')

    class Meta:
        db_table = 'campus_position_applications'
        verbose_name = '双选志愿'
        verbose_name_plural = '双选志愿'
        ordering = ['person_id', 'order']

    def __str__(self):
        return f'{self.person_id}·{self.position_id}·{self.status}'


class SelectionFlow(FullAuditModel, UUIDModel):
    """撮合流程（**按校招批次独立推进**，逆向清单 §4.3「各批次互不干扰」）。

    `wish_limit` = 该批次的志愿数量上限；为空则继承全局默认 2。
    `started` = True 后校招生**不可再修改志愿**（服务端拒绝，返回明确中文错误信息）。

    ⚠️ `published` / `published_at` 为**本实现追加**字段（契约 §4.1 未列）：
    状态机 ⑥「管理员发布双选结果」需要一个可持久化的发布态，否则「已发布」无处落库。
    仅追加、不改动契约已列字段。
    """

    batch = models.CharField(max_length=32, unique=True, verbose_name='校招批次')
    started = models.BooleanField(default=False, verbose_name='已启动')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='启动时间')
    wish_limit = models.PositiveIntegerField(null=True, blank=True, verbose_name='志愿数量上限')
    published = models.BooleanField(default=False, verbose_name='已发布结果')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='发布时间')

    class Meta:
        db_table = 'campus_selection_flows'
        verbose_name = '双选撮合流程'
        verbose_name_plural = '双选撮合流程'
        ordering = ['batch']

    def __str__(self):
        return f'{self.batch}·{"已启动" if self.started else "未启动"}'

    def effective_wish_limit(self) -> int:
        """该批次的志愿上限：批次覆盖优先，缺省继承全局默认 2（逆向清单 §4.3 ①）。"""
        return self.wish_limit or DEFAULT_WISH_LIMIT


class PlacementRecord(FullAuditModel, UUIDModel):
    """定岗跟踪主表（逆向清单 §4.3「定岗安排 · 花名册」）。

    列：姓名 / 届数 / 校招批次 / 定岗部门 / 岗位 / 定岗日期 / 目标 / 最近考核 / 状态。
    """

    class Status(models.TextChoices):
        PENDING = '待跟踪', '待跟踪'
        ONGOING = '跟踪中', '跟踪中'
        DONE = '已结束', '已结束'

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='placement_records', verbose_name='校招生',
    )
    dept = models.CharField(max_length=64, blank=True, default='', verbose_name='定岗部门')
    position_name = models.CharField(max_length=64, blank=True, default='', verbose_name='岗位')
    place_date = models.DateField(null=True, blank=True, verbose_name='定岗日期')
    track_years = models.PositiveIntegerField(default=1, verbose_name='跟踪年数')
    latest_perf = models.CharField(max_length=32, blank=True, default='', verbose_name='最近绩效')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
        verbose_name='状态', db_index=True,
    )

    class Meta:
        db_table = 'campus_placement_records'
        verbose_name = '定岗跟踪'
        verbose_name_plural = '定岗跟踪'
        ordering = ['-place_date', 'person_id']

    def __str__(self):
        return f'{self.person_id}·{self.dept}'


class PlacementGoal(FullAuditModel, UUIDModel):
    """定岗目标（逆向清单 §4.3「定岗安排 · 目标」）。"""

    record = models.ForeignKey(
        PlacementRecord, on_delete=models.CASCADE,
        related_name='goals', verbose_name='定岗记录',
    )
    name = models.CharField(max_length=128, verbose_name='目标名称')
    metric = models.CharField(max_length=64, blank=True, default='', verbose_name='衡量指标')
    target_value = models.CharField(max_length=64, blank=True, default='', verbose_name='目标值')
    weight = models.PositiveIntegerField(default=0, verbose_name='权重')
    due_date = models.DateField(null=True, blank=True, verbose_name='截止日期')
    status = models.CharField(max_length=16, blank=True, default='', verbose_name='状态')

    class Meta:
        db_table = 'campus_placement_goals'
        verbose_name = '定岗目标'
        verbose_name_plural = '定岗目标'
        ordering = ['record_id', 'name']

    def __str__(self):
        return f'{self.record_id}·{self.name}'


class PlacementMetric(FullAuditModel, UUIDModel):
    """定岗数据（逆向清单 §4.3「定岗安排 · 数据」）：月份 / 指标 / 完成值 / 备注。"""

    record = models.ForeignKey(
        PlacementRecord, on_delete=models.CASCADE,
        related_name='metrics', verbose_name='定岗记录',
    )
    ym = models.CharField(max_length=7, blank=True, default='', verbose_name='月份', db_index=True)
    metric = models.CharField(max_length=64, blank=True, default='', verbose_name='指标')
    actual_value = models.CharField(max_length=64, blank=True, default='', verbose_name='完成值')
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_placement_metrics'
        verbose_name = '定岗数据'
        verbose_name_plural = '定岗数据'
        ordering = ['record_id', 'ym']

    def __str__(self):
        return f'{self.record_id}·{self.ym}·{self.metric}'


class PlacementAssessment(FullAuditModel, UUIDModel):
    """定岗考核（逆向清单 §4.3「定岗安排 · 考核」）：考核周期 / 得分 / 绩效等级 / 评定日期 / 评语。"""

    record = models.ForeignKey(
        PlacementRecord, on_delete=models.CASCADE,
        related_name='assessments', verbose_name='定岗记录',
    )
    period = models.CharField(max_length=32, blank=True, default='', verbose_name='考核周期')
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='得分')
    perf_level = models.CharField(max_length=16, blank=True, default='', verbose_name='绩效等级')
    assessed_at = models.DateField(null=True, blank=True, verbose_name='评定日期')
    comment = models.TextField(blank=True, default='', verbose_name='评语')

    class Meta:
        db_table = 'campus_placement_assessments'
        verbose_name = '定岗考核'
        verbose_name_plural = '定岗考核'
        ordering = ['record_id', 'assessed_at']

    def __str__(self):
        return f'{self.record_id}·{self.period}'


class PriceScheme(FullAuditModel, UUIDModel):
    """定价方案（逆向清单 §4.4「定价管理」）。

    `tiers` 形如 `[{"rank":"1-10","price":1200,"floor":1000}]`
    （排名分档 → 结算单价 / 排名分档 → 底价 / 排名区间 → 交易价允许区间）。
    `type` 决定是否出现「竞价大厅」页签：FIXED 固定价 / BID 出价 / CONTEST 竞价。
    """

    class SchemeType(models.TextChoices):
        FIXED = 'FIXED', '固定价'
        BID = 'BID', '出价'
        CONTEST = 'CONTEST', '竞价'

    name = models.CharField(max_length=64, verbose_name='方案名称')
    type = models.CharField(
        max_length=16, choices=SchemeType.choices, default=SchemeType.FIXED, verbose_name='方案类型',
    )
    batch = models.CharField(max_length=32, blank=True, default='', verbose_name='校招批次')
    sel_flow_batch = models.CharField(max_length=32, blank=True, default='', verbose_name='双选流程批次')
    tiers = models.JSONField(default=list, verbose_name='排名分档')
    is_default = models.BooleanField(default=False, verbose_name='默认方案')
    enabled = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        db_table = 'campus_price_schemes'
        verbose_name = '定价方案'
        verbose_name_plural = '定价方案'
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f'{self.name}·{self.type}'


class PriceBid(FullAuditModel, UUIDModel):
    """出价记录（逆向清单 §4.4「竞价大厅」）。"""

    scheme = models.ForeignKey(
        PriceScheme, on_delete=models.CASCADE, related_name='bids', verbose_name='定价方案',
    )
    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='price_bids', verbose_name='出价人',
    )
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='出价')

    class Meta:
        db_table = 'campus_price_bids'
        verbose_name = '出价记录'
        verbose_name_plural = '出价记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.person_id}·{self.price}'


class RevenueRecord(FullAuditModel, UUIDModel):
    """输出台账（逆向清单 §4.4「收入统计」）。

    行：月份 / 校招生 / 输出部门 / 阶段 / 出勤 / 计价规则 / 单价 / 金额 / 状态。
    """

    class Status(models.TextChoices):
        PENDING = '待确认', '待确认'
        CONFIRMED = '已确认', '已确认'

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='revenue_records', verbose_name='校招生',
    )
    ym = models.CharField(max_length=7, blank=True, default='', verbose_name='月份', db_index=True)
    output_dept = models.CharField(max_length=64, blank=True, default='', verbose_name='输出部门')
    stage = models.CharField(max_length=32, blank=True, default='', verbose_name='阶段')
    attend_days = models.PositiveIntegerField(default=0, verbose_name='出勤天数')
    rule = models.CharField(max_length=64, blank=True, default='', verbose_name='计价规则')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='单价')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='金额')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
        verbose_name='状态', db_index=True,
    )

    class Meta:
        db_table = 'campus_revenue_records'
        verbose_name = '输出台账'
        verbose_name_plural = '输出台账'
        ordering = ['-ym', 'output_dept']

    def __str__(self):
        return f'{self.person_id}·{self.ym}·{self.amount}'


class Bill(FullAuditModel, UUIDModel):
    """结算账单（逆向清单 §4.4「结算账单」）。

    列：账单号 / 业务部门 / 账期 / 结算人数 / 金额 / 状态 / 确认时间。
    """

    class Status(models.TextChoices):
        PENDING = '待确认', '待确认'
        CONFIRMED = '已确认', '已确认'

    bill_no = models.CharField(max_length=32, unique=True, verbose_name='账单号')
    business_dept = models.CharField(max_length=64, blank=True, default='', verbose_name='业务部门')
    period = models.CharField(max_length=16, blank=True, default='', verbose_name='账期', db_index=True)
    person_count = models.PositiveIntegerField(default=0, verbose_name='结算人数')
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='金额')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
        verbose_name='状态', db_index=True,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='确认时间')

    class Meta:
        db_table = 'campus_bills'
        verbose_name = '结算账单'
        verbose_name_plural = '结算账单'
        ordering = ['-period', '-created_at']

    def __str__(self):
        return f'{self.bill_no}·{self.amount}'


def resolve_tier_price(tiers, rank):
    """按排名分档解析结算单价与底价（逆向清单 §4.4「定价管理」）。

    `tiers` 形如 `[{"rank": "1-10", "price": 1200, "floor": 1000}]`：
    - `rank` 支持 `"1-10"`（区间，含端点）与 `"1"`（单点）；
    - 命中返回 `(price, floor)`；未命中返回 `(None, None)`。

    「排名分档 → 结算单价 / 排名分档 → 底价 / 排名区间 → 交易价允许区间」是同一份分档表的
    三种读法，故一次性解析出单价与底价。
    """
    if rank is None:
        return None, None
    for tier in tiers or []:
        if not isinstance(tier, dict):
            continue
        span = str(tier.get('rank') or '').strip()
        if not span:
            continue
        if '-' in span:
            low, _, high = span.partition('-')
            try:
                low_i, high_i = int(low), int(high)
            except (TypeError, ValueError):
                continue
            hit = low_i <= int(rank) <= high_i
        else:
            try:
                hit = int(span) == int(rank)
            except (TypeError, ValueError):
                continue
        if hit:
            price = tier.get('price')
            floor = tier.get('floor')
            return (
                Decimal(str(price)) if price is not None else None,
                Decimal(str(floor)) if floor is not None else None,
            )
    return None, None
