"""校招轮岗领域模型（campus_rotation app）。

三张表：
- LiveRoom          直播间（轮岗资源）
- ClassRoom         班级（班级管理）
- RotationArrangement 轮岗安排（校招生轮岗生命周期）

统一基类 FullAuditModel（审计 + deleted_at 软删 + restore）+ UUIDModel（nanoid 主键）。
DELETE 走软删，不硬删。

BU 语义（见冻结方案 §0/§2.1）：BU = ATS Department 二级部门（根=0、事业群=1、BU=2）。
归属 BU 存该节点 id；写时校验 bu 节点 parent 链深度==2（parent IS NOT NULL AND
parent__parent IS NULL）。模型层不强制层级字段，校验在序列化器层完成。
"""
from datetime import date

from django.db import models, transaction
from django_fsm import FSMField, FSMModelMixin, TransitionNotAllowed, transition

from apps.campus_rotation.validators import MENTOR_ONGOING_CAPACITY
from apps.common.models import FullAuditModel, UUIDModel
from apps.core.models import Department, User


class LiveRoom(FullAuditModel, UUIDModel):
    """直播间（轮岗资源）。

    归属部门 + 归属 BU（二级部门）+ 平台（字典）+ 地点（字典）+ 容量。
    campus_count 为只读聚合字段，不落库（在序列化器层计算）。
    """

    room_no = models.CharField(
        max_length=32, unique=True, verbose_name='直播间编号',
        help_text='业务编号，自动补 LR+6 位',
    )
    name = models.CharField(max_length=128, verbose_name='直播间名称')
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='live_rooms', verbose_name='归属部门',
    )
    bu = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='live_rooms_as_bu', verbose_name='归属BU',
    )
    mentor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='直播间导师',
    )
    platform = models.CharField(max_length=32, db_index=True, verbose_name='平台')
    brand = models.CharField(
        max_length=32, blank=True, default='', db_index=True, verbose_name='品牌',
        help_text='BRAND 字典 key（S5-13 建字典）',
    )
    location = models.CharField(max_length=64, blank=True, default='', verbose_name='地点')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name='容量上限')
    social_count = models.IntegerField(default=0, verbose_name='社招人数')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')
    remark = models.TextField(blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_rotation_live_rooms'
        verbose_name = '直播间'
        verbose_name_plural = '直播间'
        ordering = ['room_no']

    def save(self, *args, **kwargs):
        # 自动补号：未设 room_no 时，事务内锁定末行取最大序号 +1，写入 LR+6 位。
        if not self.room_no:
            with transaction.atomic():
                last = (
                    LiveRoom.objects.select_for_update()
                    .filter(room_no__startswith='LR')
                    .order_by('-room_no')
                    .first()
                )
                seq = 0
                if last and last.room_no and last.room_no.startswith('LR'):
                    try:
                        seq = int(last.room_no[2:8])
                    except (ValueError, IndexError):
                        seq = 0
                seq += 1
                self.room_no = f'LR{seq:06d}'
                super().save(*args, **kwargs)
                return
        super().save(*args, **kwargs)


class ServiceDept(FullAuditModel, UUIDModel):
    """客服部门（轮岗资源）。

    对齐直播间（LiveRoom）公共资源字段；专属字段：客服主管 / 客服类型 /
    工位类型 / 是否需培训认证。
    brand 存 BRAND 字典 key（与 platform/location 同构，S5-13 建字典）；
    客服占用数由 RotationArrangement.service_dept（ONGOING）聚合，不落库。
    """

    dept_no = models.CharField(
        max_length=32, unique=True, verbose_name='客服部门编号',
        help_text='业务编号，自动补 SD+6 位',
    )
    name = models.CharField(max_length=128, verbose_name='部门名称')
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='service_depts', verbose_name='归属部门',
    )
    bu = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='service_depts_as_bu', verbose_name='归属BU',
    )
    brand = models.CharField(
        max_length=32, blank=True, default='', db_index=True, verbose_name='品牌',
        help_text='BRAND 字典 key',
    )
    location = models.CharField(max_length=64, blank=True, default='', verbose_name='地点')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name='可容纳人数')
    cs_supervisor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='客服主管',
    )
    cs_type = models.CharField(
        max_length=32, blank=True, default='', verbose_name='客服类型',
        help_text='CS_TYPE 字典 key',
    )
    workstation_type = models.CharField(
        max_length=32, blank=True, default='', verbose_name='工位类型',
        help_text='WORKSTATION_TYPE 字典 key',
    )
    need_training_cert = models.BooleanField(default=False, verbose_name='是否需培训认证')
    social_count = models.IntegerField(default=0, verbose_name='社招人数')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')
    remark = models.TextField(blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_rotation_service_depts'
        verbose_name = '客服部门'
        verbose_name_plural = '客服部门'
        ordering = ['dept_no']

    def save(self, *args, **kwargs):
        # 自动补号：未设 dept_no 时，事务内锁定末行取最大序号 +1，写入 SD+6 位。
        if not self.dept_no:
            with transaction.atomic():
                last = (
                    ServiceDept.objects.select_for_update()
                    .filter(dept_no__startswith='SD')
                    .order_by('-dept_no')
                    .first()
                )
                seq = 0
                if last and last.dept_no and last.dept_no.startswith('SD'):
                    try:
                        seq = int(last.dept_no[2:8])
                    except (ValueError, IndexError):
                        seq = 0
                seq += 1
                self.dept_no = f'SD{seq:06d}'
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
        help_text='业务编号，自动补 CL+6 位',
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
    batch = models.CharField(max_length=32, blank=True, default='', verbose_name='批次')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name='容量上限')
    remark = models.TextField(blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_rotation_class_rooms'
        verbose_name = '班级'
        verbose_name_plural = '班级'
        ordering = ['code']

    def save(self, *args, **kwargs):
        # 自动补号：未设 code 时，事务内锁定末行取最大序号 +1，写入 CL+6 位。
        if not self.code:
            with transaction.atomic():
                last = (
                    ClassRoom.objects.select_for_update()
                    .filter(code__startswith='CL')
                    .order_by('-code')
                    .first()
                )
                seq = 0
                if last and last.code and last.code.startswith('CL'):
                    try:
                        seq = int(last.code[2:8])
                    except (ValueError, IndexError):
                        seq = 0
                seq += 1
                self.code = f'CL{seq:06d}'
                super().save(*args, **kwargs)
                return
        super().save(*args, **kwargs)


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

    STAGE_CHOICES = [
        ('PENDING', '待分配'),
        ('APPROVING', '审批中'),
        ('ONGOING', '轮岗中'),
        ('DONE', '已完成'),
        ('TERMINATED', '已终止'),
    ]

    person_id = models.BigIntegerField(db_index=True, verbose_name='校招生')
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
    service_dept = models.ForeignKey(
        ServiceDept, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='arrangements', verbose_name='客服部门',
    )
    stage = FSMField(
        max_length=16, choices=STAGE_CHOICES, default='PENDING',
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
