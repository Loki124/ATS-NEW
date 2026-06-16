"""Analytics Models (PRD v4 §14.9 数据中心)

数据中心 - 报表快照
"""
from django.db import models
from apps.common.models import TimestampedModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class ReportType(models.TextChoices):
    FUNNEL = 'FUNNEL', '漏斗报表'
    DASHBOARD = 'DASHBOARD', 'HR个人看板'
    CHANNEL_ROI = 'CHANNEL_ROI', '渠道ROI'
    CUSTOM = 'CUSTOM', '自定义'


class ReportSnapshot(TimestampedModel):
    """报表快照 - 定期生成"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    name = models.CharField(max_length=200, verbose_name='报表名')
    report_type = models.CharField(max_length=32, choices=ReportType.choices, verbose_name='报表类型')
    scope = models.JSONField(default=dict, verbose_name='报表范围', help_text='{department, time_range, hr_id, ...}')
    data = models.JSONField(default=dict, verbose_name='报表数据')

    generated_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='生成时间')
    generated_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='生成人',
    )

    class Meta:
        db_table = 'report_snapshots'
        verbose_name = '报表快照'
        verbose_name_plural = verbose_name
        ordering = ['-generated_at']


class ExportTask(TimestampedModel):
    """数据导出任务"""
    class Status(models.TextChoices):
        PENDING = 'PENDING', '待执行'
        RUNNING = 'RUNNING', '执行中'
        COMPLETED = 'COMPLETED', '已完成'
        FAILED = 'FAILED', '失败'

    class Format(models.TextChoices):
        XLSX = 'XLSX', 'Excel'
        CSV = 'CSV', 'CSV'
        PDF = 'PDF', 'PDF'

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    name = models.CharField(max_length=200, verbose_name='导出名称')
    entity = models.CharField(max_length=64, verbose_name='导出实体')
    filters = models.JSONField(default=dict, verbose_name='过滤条件')
    fields = models.JSONField(default=list, verbose_name='导出字段')

    format = models.CharField(max_length=8, choices=Format.choices, default=Format.XLSX, verbose_name='格式')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, verbose_name='状态')

    file_url = models.URLField(max_length=500, blank=True, verbose_name='文件URL')
    file_size = models.IntegerField(null=True, blank=True, verbose_name='文件大小（字节）')
    row_count = models.IntegerField(null=True, blank=True, verbose_name='行数')

    requested_by = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='+', verbose_name='请求人')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    class Meta:
        db_table = 'export_tasks'
        verbose_name = '导出任务'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]
