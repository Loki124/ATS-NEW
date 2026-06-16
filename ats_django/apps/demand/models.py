"""Demand Models (PRD v4 §14.1)"""
from django.db import models
from django_fsm import FSMField, transition
from apps.common.models import FullAuditModel
from apps.process.models import RecruitmentProcess
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class DemandState(models.TextChoices):
    DRAFT = 'DRAFT', '草稿'
    PENDING = 'PENDING', '待审批'
    REJECTED = 'REJECTED', '已驳回'
    APPROVED = 'APPROVED', '已通过'
    RECRUITING = 'RECRUITING', '招聘中'
    PAUSED = 'PAUSED', '已暂停'
    COMPLETED = 'COMPLETED', '已完成'
    CANCELLED = 'CANCELLED', '已取消'


class Demand(FullAuditModel):
    """招聘需求"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    code = models.CharField(max_length=20, unique=True, verbose_name='需求编号')

    title = models.CharField(max_length=200, verbose_name='需求标题')
    department = models.ForeignKey(
        'core.Department', on_delete=models.PROTECT,
        related_name='demands', verbose_name='需求部门',
    )
    requested_by = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='requested_demands', verbose_name='需求提出人',
    )
    hr = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='assigned_demands', verbose_name='负责HR',
    )

    headcount = models.IntegerField(verbose_name='需求人数')
    filled_count = models.IntegerField(default=0, verbose_name='已招人数')
    level = models.CharField(max_length=50, blank=True, verbose_name='职级')
    position_title = models.CharField(max_length=100, blank=True, verbose_name='职务')

    process = models.ForeignKey(
        RecruitmentProcess, on_delete=models.PROTECT,
        related_name='demands', verbose_name='招聘流程',
    )
    process_version = models.CharField(max_length=20, default='1.0', verbose_name='流程版本')

    jd = models.TextField(blank=True, verbose_name='JD')
    requirements = models.TextField(blank=True, verbose_name='任职要求')

    state = FSMField(
        default=DemandState.DRAFT, db_index=True,
        protected=True, verbose_name='需求状态',
    )

    priority = models.CharField(
        max_length=8, default='P1',
        choices=[('P0', 'P0-高'), ('P1', 'P1-中'), ('P2', 'P2-低')],
        verbose_name='优先级',
    )

    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='提交时间')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审批通过时间')

    class Meta:
        db_table = 'demands'
        verbose_name = '招聘需求'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['state', 'department']),
            models.Index(fields=['hr', 'state']),
        ]

    def __str__(self):
        return f'{self.code} {self.title}'

    @transition(field=state, source=DemandState.DRAFT, target=DemandState.PENDING)
    def submit(self):
        from django.utils import timezone
        self.submitted_at = timezone.now()

    @transition(field=state, source=DemandState.PENDING, target=DemandState.APPROVED)
    def approve(self):
        from django.utils import timezone
        self.approved_at = timezone.now()

    @transition(field=state, source=DemandState.PENDING, target=DemandState.REJECTED)
    def reject(self):
        pass

    @transition(field=state, source=DemandState.APPROVED, target=DemandState.RECRUITING)
    def start_recruiting(self):
        pass

    @transition(field=state, source=DemandState.RECRUITING, target=DemandState.PAUSED)
    def pause(self):
        pass

    @transition(field=state, source=DemandState.PAUSED, target=DemandState.RECRUITING)
    def resume(self):
        pass

    @transition(field=state, source='*', target=DemandState.COMPLETED)
    def complete(self):
        pass

    @transition(field=state, source='*', target=DemandState.CANCELLED)
    def cancel(self):
        pass


class DemandApproval(FullAuditModel):
    """需求审批记录"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    demand = models.ForeignKey(
        Demand, on_delete=models.CASCADE,
        related_name='approvals', verbose_name='需求',
    )
    approver = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='+', verbose_name='审批人',
    )
    level = models.IntegerField(verbose_name='审批层级')
    result = models.CharField(
        max_length=16,
        choices=[('PENDING', '待审批'), ('APPROVED', '通过'), ('REJECTED', '驳回')],
        default='PENDING', verbose_name='审批结果',
    )
    comment = models.TextField(blank=True, verbose_name='审批意见')

    class Meta:
        db_table = 'demand_approvals'
        verbose_name = '需求审批'
        verbose_name_plural = verbose_name
        ordering = ['demand', 'level']
