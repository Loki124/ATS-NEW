"""Position Models (PRD v4 §14.2)"""
from django.db import models
from django_fsm import FSMField, transition
from apps.common.models import FullAuditModel
from apps.process.models import RecruitmentProcess
from nanoid import generate as nanoid_generate


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

    process = models.ForeignKey(
        RecruitmentProcess, on_delete=models.PROTECT,
        related_name='positions', verbose_name='使用的流程',
    )
    process_version = models.CharField(max_length=20, default='1.0', verbose_name='流程版本')

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
