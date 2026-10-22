"""校招轮岗领域模型（campus_rotation app）。

三张表：
- RotationResource  轮岗资源（直播间 / 客服部门 / 其他 三种形态合一，2026-10-22）
- ClassRoom         班级（班级管理）
- RotationArrangement 轮岗安排（校招生轮岗生命周期）

统一基类 FullAuditModel（审计 + deleted_at 软删 + restore）+ UUIDModel（nanoid 主键）。
DELETE 走软删，不硬删。

BU 语义（见冻结方案 §0/§2.1）：BU = ATS Department 二级部门，0 基层级 depth==2
（根=0、事业群=1、BU=2、三级部门=3）。归属 BU 存该节点 id；
写时校验 bu 节点的层级深度==2，判定实现收敛在 `apps/core/dept_depth.py`
（全仓唯一真相源，与前端 `utils/campus.ts` 的 `buOptions(level===2)` 对齐）。
模型层不强制层级字段，校验在序列化器层完成。
"""
from datetime import date

from django.db import IntegrityError, models, transaction
from django.db.models import IntegerField
from django.db.models.functions import Cast, Substr
from django_fsm import FSMField, FSMModelMixin, TransitionNotAllowed, transition

from apps.campus_rotation.validators import MENTOR_ONGOING_CAPACITY
from apps.common.models import FullAuditModel, UUIDModel
from apps.core.models import Department, User


class RotationResource(FullAuditModel, UUIDModel):
    """轮岗资源（2026-10-22 兵哥指令：直播间 + 客服部门整合为一体）。

    **为什么合并成一张表**：直播间与客服部门是「轮岗资源」的两种形态，业务上同属
    一份资源台账（同一套归属部门 / BU / 导师 / 容量 / 饱和度口径），拆两张表导致
    「轮岗资源」列表要 UNION、BU 汇总要写两段取数逻辑。合并后用 `resource_type`
    区分形态，一张表一套口径。

    **字段归并口径**（2026-10-22 兵哥指令）：
    | 原字段（直播间 / 客服部门） | 归并后 |
    |---|---|
    | room_no（直播间编号） / dept_no（客服部门编号） | `resource_no` 资源编号 |
    | name（直播间名称 / 部门名称） | `name` 资源名称 |
    | mentor（直播间导师） / cs_supervisor（客服主管） | `mentor` 导师 |
    | —（两表各自） | `resource_type` 资源类型（直播间/客服部门/其他） |

    **已下线的字段**（兵哥指令「客服部门中去掉品牌、客服类型、工位类型」，
    并经确认「品牌也一并去掉」）：
    - `brand`（两表都有）→ 去掉
    - `cs_type`（客服类型）→ 去掉
    - `workstation_type`（工位类型）→ 去掉
    - `need_training_cert`（是否需培训认证）→ 随客服类型一并去掉

    **保留的直播间专属字段**：`platform`（平台）—— 客服部门侧本就没有该字段，
    合并后仅对「直播间」形态有意义（其它类型留空）。

    **编号规则**（兵哥指令）：按资源类型分别取号，同前缀独立计数 ——
    直播间 `LR+4`、客服部门 `SD+4`、其他 `OT+4`。
    ⚠️ 取号必须**按类型前缀**分别统计（`LR` / `SD` / `OT` 三个独立序列），
    混在一起取 max 会让不同前缀互相干扰（如 LR0005 与 SD0009 混存时取到 9）。

    campus_count 为只读聚合字段，不落库（在序列化器层计算）。
    """

    class ResourceType(models.TextChoices):
        LIVE_ROOM = 'LIVE_ROOM', '直播间'
        SERVICE_DEPT = 'SERVICE_DEPT', '客服部门'
        OTHER = 'OTHER', '其他'

    #: 资源类型 -> 编号前缀（LR+4 / SD+4 / OT+4）
    NO_PREFIX_BY_TYPE = {
        'LIVE_ROOM': 'LR',
        'SERVICE_DEPT': 'SD',
        'OTHER': 'OT',
    }

    resource_no = models.CharField(
        max_length=32, unique=True, verbose_name='资源编号',
        help_text='业务编号，按资源类型自动补 LR+4 / SD+4 / OT+4 位',
    )
    name = models.CharField(max_length=128, verbose_name='资源名称')
    resource_type = models.CharField(
        max_length=16, choices=ResourceType.choices, default=ResourceType.LIVE_ROOM,
        db_index=True, verbose_name='资源类型',
    )
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='rotation_resources', verbose_name='归属部门',
    )
    bu = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='rotation_resources_as_bu', verbose_name='归属BU',
    )
    mentor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='导师',
        help_text='直播间导师 / 客服主管归并后的统一字段',
    )
    platform = models.CharField(
        max_length=32, blank=True, default='', db_index=True, verbose_name='平台',
        help_text='仅「直播间」形态使用（PLATFORM 字典 key）',
    )
    location = models.CharField(max_length=64, blank=True, default='', verbose_name='地点')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name='容量上限')
    social_count = models.IntegerField(default=0, verbose_name='社招人数')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')
    remark = models.TextField(blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_rotation_resources'
        verbose_name = '轮岗资源'
        verbose_name_plural = '轮岗资源'
        ordering = ['resource_no']

    def save(self, *args, **kwargs):
        """自动补号：按资源类型前缀分别取号（LR+4 / SD+4 / OT+4）。

        🔴 取号看**含软删行**的全集（唯一索引覆盖软删行，默认管理器过滤 deleted_at
          → 只看未删行会复用被删行占用的号，插入必撞唯一约束）；并发撞号则重算重试。
        🔴 **按前缀分别统计**：`LR` / `SD` / `OT` 是三个独立序列，混在一起取 max
          会互相干扰（LR0005 与 SD0009 混存 → 取到 9 → SD0010，虽不撞号但跳号）。
        🔴 **不能按字符串序取末行**：`order_by('-resource_no')` 是字典序，
          'LR99' > 'LR1000'（'9' > '1'）→ 末行不是序号最大者 → 算出的号会**倒退
          并撞已占用的号**。改为按「数字后缀」排序（Cast + 长度归一），与班级 CL
          取号同口径。
        🔴 **不能按固定切片取序号**：`resource_no[2:6]` 是写死的 4 位切片，
          存量 LR+4 以外位宽的号会被切错 → 序号归零 → 复用已占用的号 → 撞唯一约束。
          改为「剥离前缀后取全部数字」，各种位宽混存都能正确解析。
        """
        if not self.resource_no:
            prefix = self.NO_PREFIX_BY_TYPE.get(
                self.resource_type or self.ResourceType.LIVE_ROOM, 'LR',
            )
            for _attempt in range(3):
                with transaction.atomic():
                    last = (
                        RotationResource.all_objects.select_for_update()
                        .filter(resource_no__startswith=prefix)
                        .annotate(
                            _suffix=Cast(
                                Substr('resource_no', 3), output_field=IntegerField(),
                            ),
                        )
                        .order_by('-_suffix')
                        .first()
                    )
                    seq = 0
                    if last and last.resource_no and last.resource_no.startswith(prefix):
                        # 剥离前缀后取**全部**数字（兼容不同位宽的历史号混存）
                        digits = last.resource_no[len(prefix):]
                        if digits.isdigit():
                            seq = int(digits)
                    seq += 1
                    self.resource_no = f'{prefix}{seq:04d}'
                    try:
                        super().save(*args, **kwargs)
                    except IntegrityError:
                        self.resource_no = ''  # 置空 → 下一轮重新取号
                        continue
                    return
            super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)


class ClassRoom(FullAuditModel, UUIDModel):
    """班级（班级管理）。

    head_teacher 须具 HEAD_TEACHER 身份（写时校验）；hrbp 仅 User 引用。
    student_count 为只读聚合字段，不落库。（D-02 关联：个人档案「班长」字段已按需求 2-3 删除）
    capacity 为运营录入的容量上限（可空），用于班级饱和校验（方案 §3.2）。
    """

    code = models.CharField(
        max_length=32, unique=True, verbose_name='班级编号',
        help_text='业务编号，自动补 CL+3 位',
    )
    name = models.CharField(max_length=64, unique=True, verbose_name='班级名')
    head_teacher = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='班主任',
    )
    hrbp = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='HRBP',
    )
    # 2026-10-22：班级管理页下线「班主任 / HRBP / 批次」三个字段，改挂「班长」。
    # ⚠️ head_teacher / hrbp / batch **模型字段保留**（只是不再在本页维护）：
    #   · hrbp 是 campus_class 的行级隔离 scope 字段（core/entity_scope.py 依赖）；
    #   · batch / head_teacher 仍被「个人档案」详情与「轮岗安排」表单回填读取。
    class_monitor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='班长',
    )
    batch = models.CharField(max_length=32, blank=True, default='', verbose_name='批次')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name='容量上限')
    remark = models.TextField(blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_rotation_class_rooms'
        verbose_name = '班级'
        verbose_name_plural = '班级'
        ordering = ['code']

    def save(self, *args, **kwargs):
        # 自动补号：未设 code 时，事务内锁定末行取最大序号 +1，写入 CL+3 位。
        # 🔴 取号看**含软删行**的全集（唯一索引覆盖软删行，默认管理器过滤 deleted_at
        #   → 只看未删行会复用被删行占用的号，插入必撞唯一约束）；并发撞号则重算重试。
        #
        # 🔴 2026-10-22 兵哥指令：编号由 CL+6 位改为 **CL+3 位**。
        #   取号逻辑随之改两处（否则会静默出两类错号）：
        #   ① **不能按字符串序取末行**：`order_by('-code')` 是字典序，'CL99' > 'CL100000'
        #      （'9' > '1'）→ 末行不是序号最大者 → 算出的号会**倒退并撞已占用的号**。
        #      改为按「数字后缀」排序（Cast + 长度归一），与 LR/SD 的取号同口径。
        #   ② **不能按固定切片取序号**：`code[2:8]` 是写死的 6 位切片，改 3 位后
        #      'CL123' 会切成 '123'（尚可），但**存量 6 位号** 'CL000123' 会被切成
        #      '000' → 序号归零 → 复用已占用的号 → 撞唯一约束。
        #      改为「剥离前缀后取全部数字」，3 位/6 位存量混存都能正确解析。
        if not self.code:
            for _attempt in range(3):
                with transaction.atomic():
                    # 取「数字后缀最大」的那行：先按后缀长度归一（位数少的补零到同宽），
                    # 再按字典序取末行 —— 等价于按数值取 max，且能走索引、可用 select_for_update。
                    last = (
                        ClassRoom.all_objects.select_for_update()
                        .filter(code__startswith='CL')
                        .annotate(
                            _suffix=Cast(Substr('code', 3), output_field=IntegerField()),
                        )
                        .order_by('-_suffix')
                        .first()
                    )
                    seq = 0
                    if last and last.code and last.code.startswith('CL'):
                        # 剥离 'CL' 前缀后取**全部**数字（兼容 3 位新号与 6 位存量号混存）
                        digits = last.code[2:]
                        if digits.isdigit():
                            seq = int(digits)
                    seq += 1
                    self.code = f'CL{seq:03d}'
                    try:
                        super().save(*args, **kwargs)
                    except IntegrityError:
                        self.code = ''  # 置空 → 下一轮重新取号
                        continue
                    return
            super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)


class RotationArrangementStage(models.TextChoices):
    """轮岗安排阶段（``RotationArrangement.stage`` 的状态机取值）。

    2026-10-21 卡 B5：原先 ``stage`` 用裸字符串 ``default='PENDING'``，FSM 可达性
    守卫（``tests/test_fsm_state_reachability_guard.py``）靠 ``type(field.default)``
    反推枚举类 —— 裸字符串推不出来 → **该字段对守卫完全失明**（守卫自检
    ``test_every_fsm_field_has_discoverable_enum`` 判红）。改为枚举成员后守卫可覆盖
    本状态机：PENDING →(submit)→ APPROVING →(approve)→ ONGOING →(complete)→ DONE，
    ONGOING →(terminate)→ TERMINATED，APPROVING →(reject)→ PENDING。
    """
    PENDING = 'PENDING', '待分配'
    APPROVING = 'APPROVING', '审批中'
    ONGOING = 'ONGOING', '轮岗中'
    DONE = 'DONE', '已完成'
    TERMINATED = 'TERMINATED', '已终止'


class RotationArrangement(FSMModelMixin, FullAuditModel, UUIDModel):
    """轮岗安排记录（校招生轮岗生命周期）。

    person_id 关联 campus_control.Person（不建外键，避免跨 app 耦合）。
    说明（假设）：冻结方案 §2.1.3 将 person_id 标注为 BigInteger 且「同 Person.user_id
    口径」，而 Person.id 实为 nanoid CharField；为保证类型自洽、可校验且避免跨 app 外键
    耦合，此处 person_id 采用 BigInteger，语义上引用 Person.user_id（校招生的关联用户 id）。
    写时校验该 user_id 对应的 Person 存在。

    其余 FK 引用 Department / User：mentor/suggest_mentor 须 CAMPUS_MENTOR；head_teacher
    须 HEAD_TEACHER；direct_manager 防成环（不能选本人或下属）；intent_bu（CharField 存
    BU 名/编码）校验被引用部门存在且深度==2。
    """

    STAGE_CHOICES = RotationArrangementStage.choices

    # 2026-10-22：校招生档案（nanoid 口径）——人员级关联。
    #   ⚠️ 与下面的 person_id 是**两件事**：
    #      person_id      = 旧口径（BigInteger，语义 = Person.user_id 的账号 id），
    #                      dev 库里 56 名校招生全为空 → 无法按人定位轮岗；
    #                      2026-10-22 起退化为**派生镜像字段**（由 campus_person 自动回填），
    #                      校招生无系统账号时为 NULL —— 故允许为空。
    #      campus_person  = 新增的档案外键（Person 主键 nanoid）→ 按人定位轮岗的唯一可靠口径。
    #   命名避开 person_id：同名 FK 的 attname 会与既有 BigInteger 字段冲突。
    person_id = models.BigIntegerField(
        db_index=True, null=True, blank=True, verbose_name='校招生账号id',
    )
    campus_person = models.ForeignKey(
        'campus_control.Person', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='rotation_arrangements', verbose_name='校招生档案',
    )
    intent_bu = models.CharField(
        max_length=32, blank=True, default='', verbose_name='意向BU',
        help_text='二级部门（BU）名/编码（展示用）',
    )
    suggest_dept = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='建议部门',
    )
    suggest_mentor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='建议导师',
    )
    head_teacher = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='班主任',
    )
    current_dept = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='当前轮岗部门',
    )
    mentor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='导师',
    )
    direct_manager = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='直属上级',
    )
    class_room = models.ForeignKey(
        ClassRoom, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='arrangements', verbose_name='班级',
    )
    # resource「具体位置」：2026-10-22 兵哥指令，直播间 + 客服部门整合为「轮岗资源」
    # 一张表后，原先两个 FK（live_room / service_dept）**合并为一个** resource FK ——
    # 一个轮岗安排只可能处于一个位置，两个 FK 指向同一张表没有意义。
    # 🔴 「轮岗位置类型」不再单独存列（原 `location_type`）：类型由
    #   `resource.resource_type` 唯一决定 → 序列化器层派生（location_type 只读输出），
    #   避免「类型与资源错配」这类需要互斥清理的脏数据。
    # ⚠️ 存量数据：两个旧 FK 的 id 在合并时可能指向不同资源 → 由数据迁移取
    #   「live_room 优先、其次 service_dept」归并到 resource_id。
    resource = models.ForeignKey(
        RotationResource, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='arrangements', verbose_name='具体位置',
    )
    # class_monitor「班长」：轮岗安排维度的班长（User 引用）。
    # ⚠️ 与 D-02 的区别：D-02 删除的是 **ClassRoom.class_monitor**（个人档案不再展示班长）；
    #    2026-10-22 业务侧要求班级管理页重新挂「班长」，故 ClassRoom 也加回该字段，
    #    此处仍是**轮岗安排**自身的班长归属（可与班级班长不同）。
    class_monitor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='班长',
    )
    # batch「批次」：2026-10-22 班级管理页下线批次维护 → 批次改由轮岗安排自己承载
    # （选班级时可自动带入，仍可手工改）。
    batch = models.CharField(max_length=32, blank=True, default='', verbose_name='批次')
    stage = FSMField(
        max_length=16, choices=STAGE_CHOICES, default=RotationArrangementStage.PENDING,
        db_index=True, protected=True, verbose_name='阶段',
    )
    employee_status = models.CharField(
        max_length=16, blank=True, default='', verbose_name='员工状态',
    )
    rotation_start = models.DateField(null=True, blank=True, verbose_name='轮岗开始')
    rotation_end = models.DateField(null=True, blank=True, verbose_name='轮岗结束')
    rank = models.IntegerField(null=True, blank=True, verbose_name='排名')
    final_dept = models.CharField(
        max_length=64, blank=True, default='', verbose_name='定岗去向',
    )
    result = models.CharField(max_length=16, blank=True, default='', verbose_name='轮岗结果')
    note = models.TextField(blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_rotation_arrangements'
        verbose_name = '轮岗安排'
        verbose_name_plural = '轮岗安排'
        ordering = ['-created_at']

    # ───────────────────────────────────────────────────────────────────
    # FSM 流转（需求 5-4 / S5-19）：stage 流程态由 @transition 统一收口，
    # protected=True 禁止任意直写（含 queryset.update），流转只走下方方法。
    # 业务含义：PENDING →(submit)→ APPROVING →(approve)→ ONGOING
    #           →(complete)→ DONE；ONGOING →(terminate)→ TERMINATED；
    #           APPROVING →(reject)→ PENDING。DONE/TERMINATED 为硬终态。
    # ───────────────────────────────────────────────────────────────────
    def get_stage_display(self):
        """FSMField 不会自动生成 get_<field>_display，显式补上（防序列化器丢键）。"""
        return dict(self.STAGE_CHOICES).get(self.stage, self.stage)

    @transition(field=stage, source='PENDING', target='APPROVING')
    def submit(self):
        """提交轮岗安排待审批（审批闸必经）。"""

    @transition(field=stage, source='APPROVING', target='ONGOING')
    def approve(self):
        if self.mentor_id and RotationArrangement.objects.filter(
            mentor_id=self.mentor_id, stage='ONGOING', deleted_at__isnull=True,
        ).exclude(id=self.id).count() >= MENTOR_ONGOING_CAPACITY:
            raise TransitionNotAllowed('导师名额已饱和')
        self.rotation_start = self.rotation_start or date.today()

    @transition(field=stage, source='APPROVING', target='PENDING')
    def reject(self):
        """审批驳回，回到待分配。"""

    @transition(field=stage, source='ONGOING', target='DONE')
    def complete(self):
        self.rotation_end = self.rotation_end or date.today()

    @transition(field=stage, source='ONGOING', target='TERMINATED')
    def terminate(self, reason=None):
        if RotationArrangement.objects.filter(
            person_id=self.person_id, stage='ONGOING', deleted_at__isnull=True,
        ).exclude(id=self.id).exists():
            raise TransitionNotAllowed('该人员存在其他进行中的轮岗安排，无法判定终止对象')
        self.rotation_end = self.rotation_end or date.today()
        if reason:
            prefix = f'{self.note}\n' if self.note else ''
            self.note = f'{prefix}[终止原因] {reason}'


class RotationStage(FullAuditModel, UUIDModel):
    """轮岗阶段（需求 5-8 / S5-21）：支持 N 段轮岗，每段独立考核。

    🔴 G-06 修正：`stage`（RotationArrangement 的流程态）与 `stage_no`（期数）**正交**，
    不混用同一字段。本表记录每一段的具体部门 / 带教导师 / 计划与实际起止 / 考核结果。

    `assessment_status` 取值：PENDING（未判定）/ WAIVED（免考）/ REQUIRED（需考核）/
    DONE（已考核）。计算口径见 S5-22（>=15 天 → REQUIRED，<15 天 → WAIVED）。
    """

    ASSESSMENT_CHOICES = [
        ('PENDING', '未判定'),
        ('WAIVED', '免考'),
        ('REQUIRED', '需考核'),
        ('DONE', '已考核'),
    ]

    arrangement = models.ForeignKey(
        RotationArrangement, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='stages', verbose_name='轮岗安排',
    )
    stage_no = models.PositiveIntegerField(verbose_name='阶段期数')
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='阶段轮岗部门',
    )
    mentor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='阶段带教导师',
    )
    planned_start = models.DateField(null=True, blank=True, verbose_name='计划开始')
    planned_end = models.DateField(null=True, blank=True, verbose_name='计划结束')
    actual_start = models.DateField(null=True, blank=True, verbose_name='实际开始')
    actual_end = models.DateField(null=True, blank=True, verbose_name='实际结束')
    assessment_status = models.CharField(
        max_length=16, choices=ASSESSMENT_CHOICES, default='PENDING',
        verbose_name='考核状态',
    )
    # 2026-10-21 二期：考核评分（0~100，可空）。档案详情「轮岗期考核结果」的评分列、
    # 以及「轮岗均分 / 综合评分 / 综合评级」的统计口径均取自本字段。
    # assessment_result 仍是自由文本结论（可写评语），与本数值字段并存、互不覆盖。
    score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='考核评分',
    )
    assessment_result = models.TextField(blank=True, default='', verbose_name='考核结果')
    assessed_at = models.DateTimeField(null=True, blank=True, verbose_name='考核时间')
    assessed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='考核人',
    )

    class Meta:
        db_table = 'campus_rotation_stages'
        verbose_name = '轮岗阶段'
        verbose_name_plural = '轮岗阶段'
        unique_together = [('arrangement', 'stage_no')]
        ordering = ['arrangement', 'stage_no']

    def save(self, *args, **kwargs):
        """落库前套用 15 天考核规则（需求 5-9 / S5-22）。

        🔴 规则**必须在模型层**生效：若只挂序列化器，直接 ORM `create()`（导入脚本、
        管理命令、其它服务的 service）会绕过判定，出现「已判定却存 PENDING」的
        状态漂移。此处是唯一判定入口，序列化器层只负责拒收客户端直写值。

        口径：`>= ASSESSMENT_MIN_DAYS`(15) 天 → REQUIRED；不足 → WAIVED；
        日期不全 → 保持 PENDING（不阻断，由定时任务兜底）。
        已 DONE（已考核）不重判；已 WAIVED 仅在口径升级为 REQUIRED 时覆盖。
        """
        from apps.campus_rotation.services.assessment import (
            STATUS_DONE,
            STATUS_REQUIRED,
            STATUS_WAIVED,
            evaluate_assessment_status,
        )

        if self.assessment_status != STATUS_DONE:
            evaluated = evaluate_assessment_status(self)
            if evaluated == STATUS_REQUIRED or self.assessment_status != STATUS_WAIVED:
                if evaluated != self.assessment_status:
                    self.assessment_status = evaluated
                    update_fields = kwargs.get('update_fields')
                    if update_fields is not None and 'assessment_status' not in update_fields:
                        kwargs['update_fields'] = list(update_fields) + ['assessment_status']
        super().save(*args, **kwargs)


class ConcurrentPostRecord(FullAuditModel, UUIDModel):
    """兼岗记录（需求 5-2 / S5-25，本地落库 + 预留摩卡同步）。

    D-03 已定：建表 + 预留同步钩子。真实摩卡 HTTP 调用待企业 API 授权后由
    `apps/campus_rotation/services/moka_sync.py` 补齐；本期只落库并维护
    `sync_status` 状态机，**不阻塞主流程**（同步失败异步重试）。

    `person` 用字符串引用 `campus_control.Person`（跨 app FK，避免循环导入）。
    """

    SYNC_STATUS_CHOICES = [
        ('PENDING', '待同步'),
        ('SYNCED', '已同步'),
        ('FAILED', '同步失败'),
        ('SKIPPED', '已跳过'),
    ]

    person = models.ForeignKey(
        'campus_control.Person', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='concurrent_post_records',
        verbose_name='兼岗人员',
    )
    arrangement = models.ForeignKey(
        RotationArrangement, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='concurrent_post_records', verbose_name='轮岗安排',
    )
    post_type = models.CharField(max_length=32, verbose_name='兼岗类型')
    effective_from = models.DateField(verbose_name='生效起')
    effective_to = models.DateField(null=True, blank=True, verbose_name='生效止')
    sync_status = models.CharField(
        max_length=16, choices=SYNC_STATUS_CHOICES, default='PENDING',
        db_index=True, verbose_name='摩卡同步状态',
    )
    sync_request_id = models.CharField(
        max_length=64, blank=True, default='', verbose_name='摩卡请求ID',
    )
    sync_error = models.TextField(blank=True, default='', verbose_name='同步失败原因')
    synced_at = models.DateTimeField(null=True, blank=True, verbose_name='同步时间')

    class Meta:
        db_table = 'campus_rotation_concurrent_post_records'
        verbose_name = '兼岗记录'
        verbose_name_plural = '兼岗记录'
        ordering = ['-effective_from', '-created_at']

    def __str__(self):
        return f'{self.person_id}-{self.post_type}({self.sync_status})'


class RotationApproval(FullAuditModel, UUIDModel):
    """轮岗变更审批单（需求 5-5 / S5-17）。

    兼岗记录创建**免审**；更换带教导师 `mentor` / 直接上级 `direct_manager` **需审批**；
    其他字段（阶段、部门、日期）免审。

    🔴 关键行为（规格 §6.5）：**审批期间 `RotationArrangement.mentor` /
    `direct_manager` 不改** —— 改的是本申请单（old_value / new_value）。
    只有审批动作 `approve` 通过后，才由审批服务在同一事务内落字段到
    `RotationArrangement` 并写两条 AuditLog。`reject` 仅记录，不落字段。
    """

    TYPE_CHOICES = [
        ('MENTOR_CHANGE', '更换带教导师'),
        ('MANAGER_CHANGE', '更换直接上级'),
    ]

    STATUS_CHOICES = [
        ('PENDING', '待审批'),
        ('APPROVED', '已通过'),
        ('REJECTED', '已驳回'),
    ]

    arrangement = models.ForeignKey(
        RotationArrangement, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='approvals', verbose_name='轮岗安排',
    )
    change_type = models.CharField(
        max_length=16, choices=TYPE_CHOICES, verbose_name='变更类型',
    )
    # 存 user_id 字符串（Char(64)），与规格一致；不用 FK 是为了保留
    # 「人员被删除后仍可追溯申请内容」的历史快照。
    old_value = models.CharField(max_length=64, blank=True, default='', verbose_name='原值')
    new_value = models.CharField(max_length=64, blank=True, default='', verbose_name='新值')
    reason = models.TextField(blank=True, default='', verbose_name='变更原因')
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default='PENDING',
        db_index=True, verbose_name='审批状态',
    )
    approver = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='审批人',
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审批时间')
    reject_reason = models.TextField(blank=True, default='', verbose_name='驳回原因')

    class Meta:
        db_table = 'campus_rotation_approvals'
        verbose_name = '轮岗变更审批'
        verbose_name_plural = '轮岗变更审批'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.change_type}:{self.status}'
