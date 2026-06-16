"""Integration Models (PRD v4 §14.4 外部系统集成)"""
from django.db import models
from apps.common.models import TimestampedModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class IntegrationType(models.TextChoices):
    MOKA = 'MOKA', '摩卡 HRIS'
    EMAIL = 'EMAIL', '邮件服务'
    WECOM = 'WECOM', '企业微信'
    SMS = 'SMS', '短信服务'
    BACKGROUND_CHECK = 'BACKGROUND_CHECK', '背调服务'
    PORTAL = 'PORTAL', '招聘门户'


class IntegrationConfig(TimestampedModel):
    """外部系统集成配置"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    type = models.CharField(max_length=32, choices=IntegrationType.choices, unique=True, verbose_name='类型')
    name = models.CharField(max_length=100, verbose_name='名称')
    config = models.JSONField(default=dict, verbose_name='配置', help_text='API URL, Key 等敏感配置')
    field_mapping = models.JSONField(default=dict, verbose_name='字段映射')

    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='最后同步时间')

    class Meta:
        db_table = 'integration_configs'
        verbose_name = '集成配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'[{self.type}] {self.name}'


class IntegrationSyncLog(TimestampedModel):
    """集成同步日志"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    config = models.ForeignKey(
        IntegrationConfig, on_delete=models.CASCADE,
        related_name='sync_logs', verbose_name='配置',
    )
    sync_type = models.CharField(max_length=32, verbose_name='同步类型', help_text='USER_PULL/USER_PUSH/RESUME_PUSH/...')
    status = models.CharField(max_length=16, verbose_name='状态', help_text='SUCCESS/PARTIAL/FAILED')
    total_count = models.IntegerField(default=0, verbose_name='总数')
    success_count = models.IntegerField(default=0, verbose_name='成功数')
    failed_count = models.IntegerField(default=0, verbose_name='失败数')
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    class Meta:
        db_table = 'integration_sync_logs'
        verbose_name = '集成同步日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
