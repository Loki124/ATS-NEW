"""人员比例管控系统 v2.4 — 数据模型（管控人数直接承载于规则上）。

建模层次：
  ControlDimension  维度（院校标签/专业标签/性别），可单独配置。
  ControlIndicator  指标（关联维度，如 985 / 男 / 工学）。
  ControlRule       管控规则 + 人数目标（单一事实来源）：
                    适用范围(bu/position/level) + 维度 + 指标 + 年度
                    -> 目标占比 / 控制强度 / 年度目标人数 / 12 个月目标。
                    （取消原上下限 lo/hi 配置；取消独立的人数目标表 ControlHeadcount）

适用范围语义：bu / position / level 三者均空 = 「全局」（不限定）；否则按部门/职务/职级过滤。
Person 的 position（职务）/ level（职级）用于命中指定范围。

所有模型继承 FullAuditModel（审计）+ UUIDModel（nanoid 主键）；删除采用硬删。
"""
from django.db import IntegrityError, models, transaction

from apps.common.models import FullAuditModel, UUIDModel

from .constants import (
    DEGREES,
    DEPTS,
    EDUCATIONS,
    LEVELS,
    MAJORS,
    POSITIONS,
    SCHOOLS,
    SEXES,
    STATUS,
    STRENGTH,
)


def _default_monthly():
    """12 个日历月目标，默认全 0。"""
    return [0] * 12


class ControlDimension(FullAuditModel, UUIDModel):
    """维度（如 院校标签/专业标签/性别），可自由新增，可单独配置。"""

    name = models.CharField(max_length=16, unique=True, verbose_name='维度')
    code = models.CharField(max_length=16, blank=True, default='', verbose_name='编码', db_index=True)
    is_active = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        verbose_name = '管控维度'
        verbose_name_plural = '管控维度'
        ordering = ['name']

    def __str__(self):
        return self.name


class ControlIndicator(FullAuditModel, UUIDModel):
    """指标（关联维度，可单独配置）。如 985 / 男 / 工学。"""

    dimension = models.ForeignKey(
        ControlDimension, on_delete=models.CASCADE, related_name='indicators',
        verbose_name='维度'
    )
    name = models.CharField(max_length=32, verbose_name='指标名称')
    is_active = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        verbose_name = '管控指标'
        verbose_name_plural = '管控指标'
        unique_together = [('dimension', 'name')]
        ordering = ['dimension', 'name']

    def __str__(self):
        return f'{self.dimension.name}·{self.name}'


class ControlRule(FullAuditModel, UUIDModel):
    """管控规则 + 人数目标（单一事实来源）。

    适用范围：bu / position / level 均空 = 全局；否则按部门/职务/职级过滤。
    同一 (bu, position, level, dimension, indicator, year) 下所有 indicator 的 target 之和必须 == 1.0（100%），
    由批量保存端点硬校验（见 views.batch / views.with_targets）。
    人数目标（年度 + 12 个月）直接承载于规则上（指标层），取消独立 ControlHeadcount 表。

    唯一键含 is_active：允许「启用原规则 + 未启用副本」共存；副本(未启用)启用时若与某条
    is_active=True 同键规则冲突 → 副本启用接口拦截（见 services.validate_rule_unique）。
    code 为规则编号（G+4 位），由 save() 在事务内自动补号，保证唯一。
    """

    # 规则编号（G+4 位，如 G0001）；写入时由 save() 自动补号，避免撞 unique 约束 500。
    code = models.CharField(
        max_length=8, unique=True, blank=True, default='', verbose_name='规则编号'
    )
    # 是否启用：停用后 Offer 钩子实时查询 is_active=True，天然即时失效。
    is_active = models.BooleanField(default=True, verbose_name='启用')

    # 适用范围（全空 = 全局）
    bu = models.CharField(
        max_length=16, blank=True, default='',
        choices=[(d, d) for d in DEPTS], verbose_name='部门'
    )
    position = models.CharField(
        max_length=32, blank=True, default='',
        choices=[(p, p) for p in POSITIONS], verbose_name='职务'
    )
    level = models.CharField(
        max_length=32, blank=True, default='',
        choices=[(l, l) for l in LEVELS], verbose_name='职级'
    )

    dimension = models.ForeignKey(
        ControlDimension, on_delete=models.CASCADE, related_name='rules', verbose_name='维度'
    )
    indicator = models.ForeignKey(
        ControlIndicator, on_delete=models.CASCADE, related_name='rules', verbose_name='指标'
    )
    # 规划年度（人数目标所属年）；同 (适用范围, 维度, 指标, 年度) 唯一
    year = models.IntegerField(default=2026, verbose_name='规划年度')
    # 占比以小数存储（0~1）；前端以百分比输入后 ÷100
    target = models.DecimalField(max_digits=6, decimal_places=4, verbose_name='目标占比')
    strength = models.CharField(
        max_length=16, choices=[(s, s) for s in STRENGTH],
        default='硬约束', verbose_name='控制强度'
    )
    # 人数目标（管控人数）：年度目标 + 12 个月目标（指标层）
    annual_target = models.IntegerField(default=0, verbose_name='年度目标人数')
    # 长度 12，下标 0=1月 .. 11=12月
    monthly_targets = models.JSONField(default=_default_monthly, verbose_name='12个月目标')
    # v2.10：月度浮动目标（Roll-over）开关
    # 开启时：本月可用目标 = 本月额定目标 + 浮动目标（已过去月份目标合计 − 已过去月份入职且在职，负数裁 0）
    # 关闭时（默认）：与 v2.4 行为完全一致（仅按本月额定目标判定）；存量行默认 False 保证零回归。
    rollover_enabled = models.BooleanField(
        default=False, verbose_name='启用本月浮动目标',
    )

    class Meta:
        verbose_name = '管控规则'
        verbose_name_plural = '管控规则'
        # 唯一键含 is_active：启用原规则 + 未启用副本可共存；副本启用冲突由服务层拦截。
        unique_together = [('bu', 'position', 'level', 'dimension', 'indicator', 'year', 'is_active')]
        ordering = ['bu', 'position', 'level', 'dimension', 'indicator', 'year']

    def save(self, *args, **kwargs):
        """自动补号：未设 code 时，事务内锁定末行取最大序号 +1，写入 G+4 位编号。

        覆盖写端点（set_rules/batch/with_targets/import 四处 create 均不传 code）也自动拿到唯一 code，
        避免撞 unique=True 约束导致 500。
        """
        if not self.code:
            with transaction.atomic():
                last = (
                    ControlRule.objects.select_for_update()
                    .order_by('-code')
                    .first()
                )
                seq = 0
                if last and last.code and last.code.startswith('G'):
                    try:
                        seq = int(last.code[1:5])
                    except (ValueError, IndexError):
                        seq = 0
                seq += 1
                self.code = f'G{seq:04d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        scope = self.bu or '全局'
        return f'[{scope}]·{self.dimension.name}·{self.indicator.name}·{self.year}'


class Person(FullAuditModel, UUIDModel):
    """人员主数据：一行一人。counted=True 才计入核算。

    position（职务）/ level（职级）用于命中指定适用范围。
    """

    code = models.CharField(max_length=32, unique=True, verbose_name='候选人编号')
    name = models.CharField(max_length=64, verbose_name='姓名')
    bu = models.CharField(
        max_length=16, choices=[(d, d) for d in DEPTS], verbose_name='部门'
    )
    # 2026-10-22：意向部门（校招生投递的意向 BU）——与「当前轮岗部门(bu)」区分：
    #   bu  = 现在轮岗在哪个部门；intent_bu = 投递时意向去哪个部门。
    intent_bu = models.CharField(
        max_length=16, blank=True, default='',
        choices=[(d, d) for d in DEPTS], verbose_name='意向部门',
    )
    school = models.CharField(
        max_length=16, choices=[(s, s) for s in SCHOOLS], verbose_name='院校标签'
    )
    sex = models.CharField(
        max_length=4, choices=[(s, s) for s in SEXES], verbose_name='性别'
    )
    major = models.CharField(
        max_length=16, choices=[(m, m) for m in MAJORS], verbose_name='专业标签'
    )
    # 2026-10-22：专业名称（如 生物技术）——「专业标签(工学/其他)」是管控维度的分类，
    #   两者分列：标签参与比例计算，名称是教育经历里的真实专业。
    major_name = models.CharField(
        max_length=64, blank=True, default='', verbose_name='专业名称'
    )
    # 2026-10-22：招聘月份不再由表单录入（编辑弹窗已下线该字段）→ 改为可空。
    #   核算月份优先取入职日期（待入职=预计入职日期 / 在职=实际入职日期），
    #   本字段仅作历史数据兜底（calc._accounting_month 的 fallback）。
    month = models.CharField(
        max_length=8, blank=True, default='', verbose_name='招聘月份'
    )
    status = models.CharField(
        max_length=16, choices=[(s, s) for s in STATUS],
        default='在职', verbose_name='状态',
                   db_index=True,
    )
    # 日期字段：用于按「预计入职日期 / 实际入职日期」计入核算月份
    expected_entry_date = models.DateField(
        null=True, blank=True, verbose_name='预计入职日期'
    )
    actual_entry_date = models.DateField(
        null=True, blank=True, verbose_name='实际入职日期'
    )
    position = models.CharField(
        max_length=32, blank=True, default='',
        choices=[(p, p) for p in POSITIONS], verbose_name='职务'
    )
    level = models.CharField(
        max_length=32, blank=True, default='',
        choices=[(l, l) for l in LEVELS], verbose_name='职级'
    )
    counted = models.BooleanField(default=True, verbose_name='计入核算')
    # 2026-09-16: PERSON 执行面映射 — 把校招人员主数据关联到其登录用户。
    # 管理单元 PERSON 成员经此字段映射成 user_id, 在执行面 row_filter_q 中以
    # created_by__in=[user_id] 真实过滤该用户创建的候选人数据 (支持交叉管理)。
    # 用 BigIntegerField 存 User.id, 与 ManagementUnitMember.user_id 同口径,
    # 避免跨 app 外键带来的迁移依赖耦合。
    user_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, verbose_name='关联用户ID')

    # 2026-10-19 S5-10（需求 2-2）：校招生档案增强字段
    #   employee_id 工号：入职后由 HR 补录；待入职人员为空（User.employee_id 此时尚不存在）。
    #   head_teacher 班主任：User 引用；「人员管理」核心筛选条件（需求 2-2）。
    #   class_room   班级：跨 app 字符串引用 campus_rotation.ClassRoom，避免与 campus_rotation 互 import 成环。
    employee_id = models.CharField(
        max_length=50, blank=True, default='', db_index=True, verbose_name='工号'
    )
    head_teacher = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='班主任',
    )
    class_room = models.ForeignKey(
        'campus_rotation.ClassRoom', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='persons', verbose_name='班级',
    )
    # 2026-10-21 二期（校招生管理助手）：档案详情 + 人员管理筛选所需字段
    #   mentor     带教导师：与 head_teacher 同为「人员管理」核心筛选条件；
    #              轮岗期各段的导师明细见档案详情「轮岗期考核结果」（RotationStage.mentor）。
    #   school_name 院校名称：school 存的是院校**标签**（985/211/双一流/其他），
    #              详情页需要真实校名，故单独存一份。
    #   education 学历 / phone 联系电话：档案详情「基本信息」展示项。
    mentor = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='导师',
    )
    school_name = models.CharField(
        max_length=64, blank=True, default='', verbose_name='院校名称'
    )
    education = models.CharField(
        max_length=16, blank=True, default='',
        choices=[(e, e) for e in EDUCATIONS], verbose_name='学历',
    )
    # 2026-10-22：学位（与学历分列：学历=培养层次，学位=授予学位）
    degree = models.CharField(
        max_length=16, blank=True, default='',
        choices=[(d, d) for d in DEGREES], verbose_name='学位',
    )
    # 2026-10-22：HRBP（归属 HRBP）——轮岗安排里维护，档案侧只读展示
    hrbp = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='HRBP',
    )
    # 2026-10-22：批次（如 2026秋招）——轮岗安排里维护，档案侧可编辑
    batch = models.CharField(
        max_length=32, blank=True, default='', verbose_name='批次'
    )
    phone = models.CharField(
        max_length=20, blank=True, default='', verbose_name='联系电话'
    )
    # 2026-10-21：编号与「招聘系统 · 候选人管理」同源 ——
    #   校招生档案是候选人的一种：关联候选人后，候选人编号（C+8）直接作为本档案编号，
    #   校招侧不再另起一套独立序列（两套独立序列会让「C00000001」在两个系统里指两个人）。
    #   跨 app 引用用字符串（与 class_room → campus_rotation.ClassRoom 同款，避免 import 环）。
    candidate = models.ForeignKey(
        'candidate.Candidate', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='campus_persons',
        verbose_name='关联候选人',
    )

    class Meta:
        verbose_name = '人员主数据'
        verbose_name_plural = '人员主数据'
        ordering = ['bu', 'code']
        # 2026-10-08 审查 #10 (P-13): 列表/核算高频过滤 bu/position/level/school/sex/major
        # 此前仅 user_id 有索引, 其余全表扫描。__year 提取无法走索引, 应改为日期范围查询,
        # actual_entry_date 建索引支撑范围扫描。
        indexes = [
            models.Index(fields=['status', 'bu', 'school'],
                         name='idx_person_status_bu_school'),
            models.Index(fields=['status', 'position', 'level'],
                         name='idx_person_status_pos_level'),
            models.Index(fields=['status', 'major', 'sex'],
                         name='idx_person_status_major_sex'),
            models.Index(fields=['status', 'bu', 'position'],
                         name='idx_person_status_bu_pos'),
            models.Index(fields=['status', 'school', 'major'],
                         name='idx_person_status_school_major'),
            models.Index(fields=['status', 'actual_entry_date'],
                         name='idx_person_status_entry'),
        ]

    def __str__(self):
        return f'{self.code}·{self.name}'

    def save(self, *args, **kwargs):
        """编号来源（2026-10-21）：与「招聘系统 · 候选人管理」同源。

        - 关联了候选人 → 编号直接取该候选人的 code（两个系统同号，同号即同人）；
        - 未关联 → 事务内锁定末行取最大序号 +1，写入 C+8 位候选人编号；
          **取号时一并看招聘系统候选人表的最大序号**（两张表同用 C+8 序列），
          避免校招侧领到招聘系统已用掉的编号。

        录入/编辑人员未传 code 时也自动拿到唯一 C 编号，避免撞 unique=True 约束导致 500。
        """
        if self.candidate_id:
            # 候选人编号即本档案编号（软删候选人也可取，FK 指向的行仍在）
            cand = self.candidate
            if cand is not None and cand.code:
                self.code = cand.code
        if not self.code:
            # 🔴 重试：并发新建时两个事务可能算出同一个序号（唯一索引兜底报错），
            #   捕获 IntegrityError 后**新开事务**重算序号再试（快照随之刷新）。
            for _attempt in range(3):
                with transaction.atomic():
                    # 🔴 取号必须看**含软删行**的全集：code 上的唯一索引覆盖软删行，
                    #   而默认管理器过滤 deleted_at → 只看未删行会复用被删行占用的号，
                    #   插入时直接撞唯一约束（400「数据库约束冲突」）。
                    #   （实测：删掉 C00000057 后再建人，仍领到 C00000057 → 必撞。）
                    # ⚠️ 2026-10-23 修复：取号必须**精确匹配 C + 8 位数字**,
                    #    不能用 `startswith='C'` ——
                    #    `import_campus_lifecycle_data` 引入的 `CS` 前缀编号
                    #    （CS00000878，实测 ats_dev 有 878 条）同样以 C 开头,
                    #    会被 `.order_by('-code')` 选中 → `int('S0000087')` 解析失败
                    #    → seq 归 0 → 去抢已被占用的 C00000001 → IntegrityError
                    #    → 重试 3 次仍是同一号 → 落到 `super().save()` 写入空 code
                    #    → 撞 unique ⇒ **新建档案直接 500**。
                    last = (
                        Person.all_objects.select_for_update()
                        .filter(code__regex=r'^C[0-9]{8}$')
                        .order_by('-code')
                        .first()
                    )
                    seq = 0
                    if last and last.code and last.code.startswith('C'):
                        try:
                            seq = int(last.code[1:9])
                        except (ValueError, IndexError):
                            seq = 0
                    # 招聘系统候选人表同用 C+8 序列 → 取两表最大，避免跨表撞号
                    # （局部导入：candidate app 依赖 campus_control.constants，避免 app 间 import 环）
                    from apps.candidate.models import Candidate
                    cand_last = (
                        Candidate.all_objects.filter(code__regex=r'^C[0-9]{8}$')
                        .order_by('-code').first()
                    )
                    if cand_last and cand_last.code and cand_last.code.startswith('C'):
                        try:
                            seq = max(seq, int(cand_last.code[1:9]))
                        except (ValueError, IndexError):
                            pass
                    seq += 1
                    self.code = f'C{seq:08d}'
                    try:
                        super().save(*args, **kwargs)
                    except IntegrityError:
                        self.code = ''  # 置空 → 下一轮重新取号
                        continue
                    return
            # 连续撞号 → 交由上层统一转成 400 提示
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class PersonDimensionValue(FullAuditModel, UUIDModel):
    """人员动态维度取值（如 身份证籍贯=江苏）。

    与写死的 school/sex/major 三个 legacy 维度解耦：任何在「维度管理」中新增的维度，
    其人员取值都落到本表，计算引擎通过 __dim__<维度名> 读取，无需改代码。
    """

    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name='dimension_values', verbose_name='人员'
    )
    dimension = models.ForeignKey(
        ControlDimension, on_delete=models.CASCADE, related_name='person_values', verbose_name='维度'
    )
    value = models.CharField(max_length=64, verbose_name='取值')

    class Meta:
        verbose_name = '人员维度取值'
        verbose_name_plural = '人员维度取值'
        unique_together = [('person', 'dimension')]
        ordering = ['person', 'dimension']

    def __str__(self):
        return f'{self.person.code}·{self.dimension.name}={self.value}'
