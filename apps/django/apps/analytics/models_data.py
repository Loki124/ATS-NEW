"""G35 DataSubscription 模型 - 2026-06-30 stub 升级为完整字段 (对齐 FE api/data.ts)

原 stub 仅 name/created_at; 现补齐订阅所需的全部字段, 与
DataSubscriptionSerializer / FE DataSubscription interface 保持一致.
"""
from django.db import models


class DataSubscription(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name='ID')
    name = models.CharField(max_length=100, blank=True, default='', verbose_name='名称')
    user_id = models.CharField(max_length=64, blank=True, default='', verbose_name='订阅人ID')
    user_name = models.CharField(max_length=100, blank=True, default='', verbose_name='订阅人')
    resource = models.CharField(max_length=32, blank=True, default='', verbose_name='资源')
    metric = models.CharField(max_length=32, blank=True, default='all', verbose_name='指标')
    filters = models.TextField(blank=True, default='', verbose_name='过滤条件')
    channel = models.CharField(max_length=16, blank=True, default='SYSTEM', verbose_name='渠道')
    schedule = models.CharField(max_length=16, blank=True, default='DAILY', verbose_name='周期')
    schedule_time = models.CharField(max_length=8, blank=True, default='', verbose_name='发送时间')
    recipients = models.TextField(blank=True, default='', verbose_name='收件人')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name='上次运行')
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name='下次运行')
    run_count = models.IntegerField(default=0, verbose_name='运行次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        app_label = 'analytics'
        db_table = 'analytics_data_subscription'
        ordering = ['-created_at']
        verbose_name = '数据订阅'
        verbose_name_plural = verbose_name
