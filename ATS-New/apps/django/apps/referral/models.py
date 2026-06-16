"""Referral Models (PRD v4 §3.1, §6.4 N+1/N+2 推荐)"""
from django.db import models
from apps.common.models import FullAuditModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class ReferralType(models.TextChoices):
    N_PLUS_1 = 'N+1', 'N+1 推荐（直接下属推荐）'
    N_PLUS_2 = 'N+2', 'N+2 推荐（隔级下属推荐）'
    INTERNAL = 'INTERNAL', '内部推荐'
    SOCIAL = 'SOCIAL', '社会推荐'


class ReferralStatus(models.TextChoices):
    SUBMITTED = 'SUBMITTED', '已提交'
    PROCESSING = 'PROCESSING', '处理中'
    HIRED = 'HIRED', '已入职'
    FAILED = 'FAILED', '未通过'
    WITHDRAWN = 'WITHDRAWN', '已撤回'


class Referral(FullAuditModel):
    """推荐记录"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    referrer = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='referrals', verbose_name='推荐人',
    )
    candidate = models.ForeignKey(
        'candidate.Candidate', on_delete=models.PROTECT,
        related_name='referrals', verbose_name='候选人',
    )
    position = models.ForeignKey(
        'position.Position', on_delete=models.PROTECT,
        related_name='referrals', verbose_name='推荐职位',
    )
    referral_type = models.CharField(
        max_length=8, choices=ReferralType.choices,
        db_index=True, verbose_name='推荐类型',
    )

    # N+1/N+2 检测结果
    detected_type = models.CharField(
        max_length=8, blank=True, verbose_name='自动检测类型',
        help_text='系统自动检测的推荐类型',
    )
    detection_detail = models.JSONField(default=dict, verbose_name='检测详情')

    status = models.CharField(
        max_length=16, choices=ReferralStatus.choices,
        default=ReferralStatus.SUBMITTED, db_index=True, verbose_name='状态',
    )

    # 奖金（V4.5 接入财务）
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='奖金金额')
    bonus_paid_at = models.DateTimeField(null=True, blank=True, verbose_name='奖金发放时间')

    note = models.TextField(blank=True, verbose_name='推荐理由')

    class Meta:
        db_table = 'referrals'
        verbose_name = '推荐记录'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['referrer', 'status']),
            models.Index(fields=['referral_type', 'status']),
        ]

    def __str__(self):
        return f'{self.referrer.full_name} 推荐 {self.candidate.name} ({self.referral_type})'
