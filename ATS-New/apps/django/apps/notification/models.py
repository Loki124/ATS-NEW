"""Notification Models (PRD v4 §14.10)"""
from django.db import models
from apps.common.models import TimestampedModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class NotificationChannel(models.TextChoices):
    IN_APP = 'IN_APP', '站内信'
    EMAIL = 'EMAIL', '邮件'
    SMS = 'SMS', '短信'
    WECOM = 'WECOM', '企微'


class NotificationTemplate(TimestampedModel):
    """通知模板"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    code = models.CharField(max_length=100, unique=True, verbose_name='模板编码',
        help_text='如 offer.sent / interview.scheduled / stage.advanced')
    name = models.CharField(max_length=100, verbose_name='模板名称')

    # 触发事件
    event = models.CharField(max_length=100, db_index=True, verbose_name='触发事件')

    # 模板内容（按 channel 分）
    templates = models.JSONField(default=dict, verbose_name='多通道模板',
        help_text='{"IN_APP": "...", "EMAIL": {"subject": "...", "body": "..."}, "SMS": "...", "WECOM": "..."}')

    # 变量定义
    variables = models.JSONField(default=list, verbose_name='可用变量',
        help_text='[{"name": "candidate_name", "type": "string", "required": true, "example": "张三"}]')

    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    class Meta:
        db_table = 'notification_templates'
        verbose_name = '通知模板'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'[{self.code}] {self.name}'


class NotificationLog(TimestampedModel):
    """通知发送日志"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='logs', verbose_name='模板',
    )

    recipient = models.ForeignKey(
        'core.User', on_delete=models.CASCADE,
        related_name='notifications', verbose_name='接收人',
    )
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices, verbose_name='通道')

    # 内容快照
    subject = models.CharField(max_length=200, blank=True, verbose_name='主题')
    content = models.TextField(verbose_name='内容')

    # 事件上下文
    event = models.CharField(max_length=100, db_index=True, verbose_name='事件')
    context = models.JSONField(default=dict, verbose_name='上下文')

    # 状态
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='发送时间')
    read_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='已读时间')
    failed_reason = models.TextField(blank=True, verbose_name='失败原因')

    class Meta:
        db_table = 'notification_logs'
        verbose_name = '通知日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'read_at']),
            models.Index(fields=['event', 'created_at']),
        ]
