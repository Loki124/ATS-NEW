"""Invitation Models (PRD v4 §14.6 邀约)"""
from django.db import models
from django_fsm import FSMField, transition
from apps.common.models import FullAuditModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class InvitationState(models.TextChoices):
    PENDING = 'PENDING', '待邀约'
    INVITING = 'INVITING', '邀约中'
    SUCCESS = 'SUCCESS', '邀约成功'
    FAILED = 'FAILED', '邀约失败'
    TIMEOUT = 'TIMEOUT', '已超时'


class Invitation(FullAuditModel):
    """邀约"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    application = models.ForeignKey(
        'application.Application', on_delete=models.CASCADE,
        related_name='invitations', verbose_name='申请',
    )
    inviter = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='sent_invitations', verbose_name='邀约人',
    )

    invited_at = models.DateTimeField(auto_now_add=True, verbose_name='邀约时间')
    response_at = models.DateTimeField(null=True, blank=True, verbose_name='响应时间')
    expire_at = models.DateTimeField(verbose_name='过期时间')

    # 抢单模式
    is_grab_pool = models.BooleanField(default=False, verbose_name='抢单池')
    grabbed_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='抢单人',
    )
    grabbed_at = models.DateTimeField(null=True, blank=True, verbose_name='抢单时间')

    # 响应内容
    candidate_response = models.CharField(max_length=32, blank=True, verbose_name='候选人响应',
        help_text='AGREE/REJECT/CALLBACK/NO_RESPONSE')
    candidate_note = models.TextField(blank=True, verbose_name='候选人备注')

    state = FSMField(
        default=InvitationState.PENDING, db_index=True,
        protected=True, verbose_name='邀约状态',
    )

    class Meta:
        db_table = 'invitations'
        verbose_name = '邀约'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['state', 'expire_at']),
            models.Index(fields=['is_grab_pool', 'state']),
        ]

    def __str__(self):
        return f'Invitation[{self.application.code}] {self.state}'

    @transition(field=state, source=InvitationState.PENDING, target=InvitationState.INVITING)
    def start_inviting(self):
        pass

    @transition(field=state, source=InvitationState.INVITING, target=InvitationState.SUCCESS)
    def succeed(self):
        from django.utils import timezone
        self.response_at = timezone.now()

    @transition(field=state, source=InvitationState.INVITING, target=InvitationState.FAILED)
    def fail(self, response='', note=''):
        from django.utils import timezone
        self.response_at = timezone.now()
        self.candidate_response = response
        self.candidate_note = note

    @transition(field=state, source=[InvitationState.PENDING, InvitationState.INVITING], target=InvitationState.TIMEOUT)
    def timeout(self):
        pass
