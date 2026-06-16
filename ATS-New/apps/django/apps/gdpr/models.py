"""GDPR Models (PRD v4 §4.4)"""
from django.db import models
from apps.common.models import TimestampedModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class GDPRRequestType(models.TextChoices):
    FORGET = 'FORGET', '被遗忘权（删除）'
    EXPORT = 'EXPORT', '数据导出'
    RECTIFY = 'RECTIFY', '数据更正'


class GDPRRequestStatus(models.TextChoices):
    PENDING = 'PENDING', '待处理'
    PROCESSING = 'PROCESSING', '处理中'
    COMPLETED = 'COMPLETED', '已完成'
    REJECTED = 'REJECTED', '已拒绝'


class GDPRRequest(TimestampedModel):
    """GDPR 请求"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        'candidate.Candidate', on_delete=models.PROTECT,
        related_name='gdpr_requests', verbose_name='候选人',
    )
    request_type = models.CharField(max_length=16, choices=GDPRRequestType.choices, verbose_name='请求类型')
    status = models.CharField(
        max_length=16, choices=GDPRRequestStatus.choices,
        default=GDPRRequestStatus.PENDING, db_index=True, verbose_name='状态',
    )

    # 处理
    processed_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='处理人',
    )
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')
    result = models.TextField(blank=True, verbose_name='处理结果')
    reject_reason = models.TextField(blank=True, verbose_name='拒绝原因')

    # 候选人提交信息
    submitted_email = models.EmailField(blank=True, verbose_name='提交邮箱')
    verification_code = models.CharField(max_length=10, blank=True, verbose_name='验证码')

    class Meta:
        db_table = 'gdpr_requests'
        verbose_name = 'GDPR 请求'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['candidate', 'request_type']),
        ]
