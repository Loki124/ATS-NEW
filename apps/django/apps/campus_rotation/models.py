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
from django.db import models, transaction

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


class ClassRoom(FullAuditModel, UUIDModel):
    """班级（班级管理）。

    head_teacher 须具 HEAD_TEACHER 身份（写时校验）；class_monitor 仅 User 引用，
    不建身份类型；hrbp 仅 User 引用。student_count 为只读聚合字段，不落库。
    """

    code = models.CharField(
        max_length=32, unique=True, verbose_name='班级编号',
        help_text='业务编号，自动补 CL+6 位',
    )
    name = models.CharField(max_length=64, verbose_name='班级名')
    head_teacher = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='班主任',
    )
    class_monitor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='班长',
    )
    hrbp = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='HRBP',
    )
    batch = models.CharField(max_length=32, blank=True, default='', verbose_name='批次')
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


class RotationArrangement(FullAuditModel, UUIDModel):
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
    stage = models.CharField(
        max_length=16, choices=STAGE_CHOICES, default='PENDING',
        db_index=True, verbose_name='阶段',
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
