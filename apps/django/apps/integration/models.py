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
    """外部系统集成配置

    Fix 6: 新增 encrypted_secret 字段, 用 Fernet 加密敏感凭据.
    config JSON 保留为非敏感配置 (URL / 签名名 / 模板号 等).
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    type = models.CharField(max_length=32, choices=IntegrationType.choices, verbose_name='类型')
    provider = models.CharField(max_length=64, blank=True, default='', db_index=True, verbose_name='供应商代码', help_text='背调场景下区分多家供应商，如 quanjing/xinda/andun')
    name = models.CharField(max_length=100, verbose_name='名称')
    config = models.JSONField(default=dict, verbose_name='非敏感配置', help_text='API URL, 签名名, 模板号 等')
    encrypted_secret = models.TextField(blank=True, verbose_name='加密凭据 (Fernet)', help_text='JSON: {"corp_secret":"...", "access_key_secret":"..."} 加密后')
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
    endpoint = models.CharField(max_length=255, blank=True, default='', verbose_name='接口路径')
    method = models.CharField(max_length=16, blank=True, default='', verbose_name='请求方法')
    direction = models.CharField(max_length=8, blank=True, default='', verbose_name='方向', help_text='OUT 出向 / IN 入向')
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name='耗时(ms)')
    # 2026-08-28 寇豆码: 回调入向新增字段
    # request_data 存完整回调体（便于审计/排障）；external_ref 存供应商单号（number）便于幂等与展示
    request_data = models.JSONField(null=True, blank=True, verbose_name='原始请求体', help_text='回调等入向请求的原始负载，便于审计与排障')
    external_ref = models.CharField(max_length=128, blank=True, default='', db_index=True, verbose_name='外部单号', help_text='供应商订单号/回执号(number)，便于幂等与展示')

    class Meta:
        db_table = 'integration_sync_logs'
        verbose_name = '集成同步日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            # 回调幂等查询 (config, sync_type, external_ref, status) 加速
            models.Index(
                fields=['config', 'sync_type', 'external_ref', 'status'],
                name='idx_synclog_cb_idem',
            ),
        ]
