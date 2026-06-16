"""Offer Models (PRD v4 §6.6, §14.5)"""
from django.db import models
from django_fsm import FSMField, transition
from apps.common.models import FullAuditModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class OfferState(models.TextChoices):
    DRAFT = 'DRAFT', '草稿'
    PENDING_APPROVAL = 'PENDING_APPROVAL', '待审批'
    REJECTED = 'REJECTED', '已驳回'
    PENDING_SEND = 'PENDING_SEND', '待发出'
    SENT = 'SENT', '已发出'
    NEGOTIATING = 'NEGOTIATING', '谈判中'
    ACCEPTED = 'ACCEPTED', '已接受'
    REJECTED_BY_CANDIDATE = 'REJECTED_BY_CANDIDATE', '候选人已拒绝'
    WITHDRAWN = 'WITHDRAWN', '已撤回'
    PENDING_ONBOARDING = 'PENDING_ONBOARDING', '待入职'
    ONBOARDED = 'ONBOARDED', '已入职'


class Offer(FullAuditModel):
    """Offer"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    code = models.CharField(max_length=20, unique=True, verbose_name='Offer编号')

    application = models.OneToOneField(
        'application.Application', on_delete=models.PROTECT,
        related_name='offer', verbose_name='申请',
    )
    candidate = models.ForeignKey(
        'candidate.Candidate', on_delete=models.PROTECT,
        related_name='offers', verbose_name='候选人',
    )
    position = models.ForeignKey(
        'position.Position', on_delete=models.PROTECT,
        related_name='offers', verbose_name='职位',
    )

    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='薪资')
    salary_currency = models.CharField(max_length=8, default='CNY', verbose_name='币种')
    level = models.CharField(max_length=50, blank=True, verbose_name='职级')
    position_title = models.CharField(max_length=100, blank=True, verbose_name='职务')

    start_date = models.DateField(null=True, blank=True, verbose_name='预计入职日期')
    expire_date = models.DateField(null=True, blank=True, verbose_name='Offer过期日期')

    # 审批
    approver = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='审批人',
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审批时间')

    # 候选人响应
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='发送时间')
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name='候选人响应时间')
    rejection_reason = models.TextField(blank=True, verbose_name='拒绝原因')

    state = FSMField(
        default=OfferState.DRAFT, db_index=True,
        protected=True, verbose_name='Offer状态',
    )

    class Meta:
        db_table = 'offers'
        verbose_name = 'Offer'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['state', 'created_at']),
            models.Index(fields=['candidate', 'state']),
        ]

    def __str__(self):
        return f'{self.code} {self.candidate.name}'

    @transition(field=state, source=OfferState.DRAFT, target=OfferState.PENDING_APPROVAL)
    def submit_approval(self):
        pass

    @transition(field=state, source=OfferState.PENDING_APPROVAL, target=OfferState.PENDING_SEND)
    def approve(self):
        from django.utils import timezone
        self.approved_at = timezone.now()

    @transition(field=state, source=OfferState.PENDING_APPROVAL, target=OfferState.REJECTED)
    def reject(self):
        pass

    @transition(field=state, source=OfferState.PENDING_SEND, target=OfferState.SENT)
    def send(self):
        from django.utils import timezone
        self.sent_at = timezone.now()

    @transition(field=state, source=OfferState.SENT, target=OfferState.ACCEPTED)
    def accept(self):
        from django.utils import timezone
        self.responded_at = timezone.now()

    @transition(field=state, source=OfferState.SENT, target=OfferState.NEGOTIATING)
    def negotiate(self):
        from django.utils import timezone
        self.responded_at = timezone.now()

    @transition(field=state, source=OfferState.SENT, target=OfferState.REJECTED_BY_CANDIDATE)
    def candidate_reject(self, reason=''):
        from django.utils import timezone
        self.responded_at = timezone.now()
        self.rejection_reason = reason

    @transition(field=state, source=OfferState.ACCEPTED, target=OfferState.PENDING_ONBOARDING)
    def set_onboarding_date(self, date):
        self.start_date = date

    @transition(field=state, source=OfferState.PENDING_ONBOARDING, target=OfferState.ONBOARDED)
    def onboarded(self):
        pass
