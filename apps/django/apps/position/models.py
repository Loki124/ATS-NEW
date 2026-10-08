"""Position Models (PRD v4 §14.2)"""
from django.db import models
from django_fsm import FSMField, transition
from nanoid import generate as nanoid_generate

from apps.common.models import FullAuditModel
from apps.process.models import RecruitmentProcess
from apps.reason_library.models import RECRUIT_TYPE_CHOICES, RecruitType


def gen_id():
    return nanoid_generate(size=21)


class PositionState(models.TextChoices):
    DRAFT = 'DRAFT', '草稿'
    PENDING_PUBLISH = 'PENDING_PUBLISH', '待发布'
    PUBLISHED = 'PUBLISHED', '已发布'
    RECRUITING = 'RECRUITING', '招聘中'
    PAUSED = 'PAUSED', '已暂停'
    UNPUBLISHED = 'UNPUBLISHED', '已下架'
    CLOSED = 'CLOSED', '已关闭'


class Position(FullAuditModel):
    """职位"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    # 招聘类型硬分区 (social/campus): 社会/校园招聘数据相互隔离, 历史数据默认 social.
    recruit_type = models.CharField(
        max_length=16, choices=RECRUIT_TYPE_CHOICES, default=RecruitType.SOCIAL.value,
        db_index=True, verbose_name='招聘类型',
    )
    code = models.CharField(max_length=20, unique=True, verbose_name='职位编号')

    title = models.CharField(max_length=100, db_index=True, verbose_name='职位名称')
    description = models.TextField(blank=True, verbose_name='职位描述')
    requirements = models.TextField(blank=True, verbose_name='任职要求')

    department = models.ForeignKey(
        'core.Department', on_delete=models.PROTECT,
        related_name='positions', verbose_name='所属部门',
    )
    hiring_manager = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='hiring_manager_positions', verbose_name='用人经理',
    )
    owner = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='owned_positions', verbose_name='职位负责人',
    )
    assistants = models.ManyToManyField(
        'core.User', blank=True,
        related_name='assisted_positions', verbose_name='职位协助人',
    )

    level = models.CharField(max_length=50, blank=True, verbose_name='职级')
    position_title = models.CharField(max_length=100, blank=True, verbose_name='职务')
    location = models.CharField(max_length=100, blank=True, verbose_name='工作地点')
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='薪资下限')
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='薪资上限')

    headcount = models.IntegerField(default=1, verbose_name='招聘人数')
    filled_count = models.IntegerField(default=0, verbose_name='已招人数')

    # 优先级：高/中/低（业务简单枚举，无独立表）
    priority = models.CharField(
        max_length=10,
        choices=[('高', '高'), ('中', '中'), ('低', '低')],
        default='中', blank=True, verbose_name='优先级',
    )

    # T9/G1 路径 (c)：Demand ↔ Position 之前**没有**任何外键关联，
    # `demand.positions` 在运行时是 AttributeError（`positions` 是 Position.process
    # 的反向名，即 `process.positions`）。需求升级要"升 Demand 及其 Positions"，
    # 只有显式外键才能给"该需求的职位"一个确定定义；按 process_id 反查会把**其他需求**
    # 的职位一并改指（跨需求污染）。
    demand = models.ForeignKey(
        'demand.Demand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='positions',
        verbose_name='所属需求',
        help_text='可空：职位可脱离需求独立存在；存量职位 demand_id 一律 NULL（归属无法反推）',
    )

    process = models.ForeignKey(
        RecruitmentProcess, on_delete=models.PROTECT,
        related_name='positions', verbose_name='使用的流程',
    )
    # T9/G2：与 RecruitmentProcess.current_version（default 'V1.0'）以及 service 层
    # 实际写入值（position/services.py 写 process.current_version，带 V 前缀）对齐。
    # 旧 default '1.0' 与真实写入自相矛盾，且 time_limit 按版本字符串精确匹配时
    # 格式漂移会静默匹配空集（fail-silent）。
    process_version = models.CharField(max_length=20, default='V1.0', verbose_name='流程版本')

    state = FSMField(
        default=PositionState.DRAFT, db_index=True,
        protected=True, verbose_name='职位状态',
    )

    published_at = models.DateTimeField(null=True, blank=True, verbose_name='发布时间')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='关闭时间')

    class Meta:
        db_table = 'positions'
        verbose_name = '职位'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['department', 'state']),
            models.Index(fields=['hiring_manager', 'state']),
        ]

    def __str__(self):
        return f'{self.code} {self.title}'

    @transition(field=state, source=PositionState.DRAFT, target=PositionState.PENDING_PUBLISH)
    def submit_publish(self):
        pass

    @transition(field=state, source=[PositionState.PENDING_PUBLISH, PositionState.PAUSED, PositionState.UNPUBLISHED], target=PositionState.PUBLISHED)
    def publish(self):
        from django.utils import timezone
        self.published_at = timezone.now()

    @transition(field=state, source=PositionState.PUBLISHED, target=PositionState.RECRUITING)
    def start_recruiting(self):
        pass

    @transition(field=state, source=[PositionState.PUBLISHED, PositionState.RECRUITING], target=PositionState.PAUSED)
    def pause(self):
        pass

    @transition(field=state, source=PositionState.PAUSED, target=PositionState.RECRUITING)
    def resume(self):
        pass

    @transition(field=state, source='*', target=PositionState.CLOSED)
    def close(self):
        from django.utils import timezone
        self.closed_at = timezone.now()
