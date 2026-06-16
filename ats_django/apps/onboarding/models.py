"""Onboarding Models (PRD v4 §6.7)"""
from django.db import models
from django_fsm import FSMField, transition
from apps.common.models import FullAuditModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class OnboardingState(models.TextChoices):
    PENDING = 'PENDING', '待入职'
    PREPARING = 'PREPARING', '入职准备中'
    DELAYED = 'DELAYED', '已延期'
    COMPLETED = 'COMPLETED', '已完成'
    PROBATION = 'PROBATION', '试用中'
    REGULARIZED = 'REGULARIZED', '已转正'
    RESIGNED_DURING_PROBATION = 'RESIGNED_DURING_PROBATION', '试用期离职'


class Onboarding(FullAuditModel):
    """入职流程"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    offer = models.OneToOneField(
        'offer.Offer', on_delete=models.PROTECT,
        related_name='onboarding', verbose_name='Offer',
    )
    candidate = models.ForeignKey(
        'candidate.Candidate', on_delete=models.PROTECT,
        related_name='onboardings', verbose_name='候选人',
    )
    position = models.ForeignKey(
        'position.Position', on_delete=models.PROTECT,
        related_name='onboardings', verbose_name='职位',
    )

    start_date = models.DateField(verbose_name='入职日期')
    actual_start_date = models.DateField(null=True, blank=True, verbose_name='实际入职日期')
    probation_end_date = models.DateField(null=True, blank=True, verbose_name='试用期结束日期')

    todo_list = models.JSONField(default=list, verbose_name='入职待办清单')
    todo_completed = models.JSONField(default=dict, verbose_name='待办完成情况')

    state = FSMField(
        default=OnboardingState.PENDING, db_index=True,
        protected=True, verbose_name='入职状态',
    )

    regularization_result = models.CharField(max_length=32, blank=True, verbose_name='转正结果')
    regularization_at = models.DateTimeField(null=True, blank=True, verbose_name='转正时间')

    class Meta:
        db_table = 'onboardings'
        verbose_name = '入职流程'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['state', 'start_date']),
        ]

    def __str__(self):
        return f'{self.candidate.name} 入职 {self.start_date}'

    @transition(field=state, source=OnboardingState.PENDING, target=OnboardingState.PREPARING)
    def start_preparing(self):
        pass

    @transition(field=state, source=OnboardingState.PREPARING, target=OnboardingState.COMPLETED)
    def complete(self):
        from django.utils import timezone
        self.actual_start_date = self.start_date

    @transition(field=state, source=[OnboardingState.PREPARING, OnboardingState.DELAYED], target=OnboardingState.DELAYED)
    def delay(self, new_date):
        self.start_date = new_date

    @transition(field=state, source=OnboardingState.DELAYED, target=OnboardingState.PREPARING)
    def resume(self):
        pass

    @transition(field=state, source=OnboardingState.COMPLETED, target=OnboardingState.PROBATION)
    def enter_probation(self):
        from datetime import timedelta
        if not self.probation_end_date:
            self.probation_end_date = self.start_date + timedelta(days=90)

    @transition(field=state, source=OnboardingState.PROBATION, target=OnboardingState.REGULARIZED)
    def regularize(self, result='PASS'):
        from django.utils import timezone
        self.regularization_result = result
        self.regularization_at = timezone.now()
