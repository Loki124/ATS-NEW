"""制度公告模型 — 招聘专家查看招聘相关制度与公告内容。"""
from django.db import models
from django.utils import timezone

from apps.common.models import FullAuditModel


class Announcement(FullAuditModel):
    """制度 / 公告 / 流程类内容。

    用于工作台「制度公告」模块（招聘专家查看）与设置页管理后台（HR 及以上维护）。
    """

    CATEGORY_CHOICES = [
        ('SYSTEM', '制度'),
        ('NOTICE', '公告'),
        ('PROCESS', '流程'),
    ]
    AUDIENCE_CHOICES = [
        ('RECRUIT_EXPERT', '招聘专家'),
        ('ALL', '全员'),
    ]

    title = models.CharField(max_length=200, verbose_name='标题')
    category = models.CharField(
        max_length=16, choices=CATEGORY_CHOICES, default='SYSTEM',
        verbose_name='分类',
    )
    audience = models.CharField(
        max_length=16, choices=AUDIENCE_CHOICES, default='RECRUIT_EXPERT',
        verbose_name='受众',
    )
    summary = models.TextField(blank=True, default='', verbose_name='概述')
    body = models.TextField(verbose_name='正文')
    pinned = models.BooleanField(default=False, verbose_name='置顶')
    published_at = models.DateTimeField(default=timezone.now, verbose_name='发布时间')
    is_active = models.BooleanField(default=True, verbose_name='上架')
    # 单条公告的展示位置（由两个独立开关控制，可同时开）：
    # - show_on_workbench: 是否在工作台「政策制度」卡片中展示。
    # - show_in_more: 是否在「更多 / 快捷入口」中提供该公告入口。
    show_on_workbench = models.BooleanField(default=True, verbose_name='工作台展示')
    show_in_more = models.BooleanField(default=False, verbose_name='更多中展示')

    class Meta:
        verbose_name = '制度公告'
        verbose_name_plural = '制度公告'
        ordering = ['-pinned', '-published_at']

    def save(self, *args, **kwargs):
        # 业务规则：已发布的公告都要在「更多」中展示；下架则不在更多展示。
        self.show_in_more = bool(self.is_active)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_category_display()} · {self.title}'


class AnnouncementAttachment(FullAuditModel):
    """制度公告附件 — 上传的 PDF / Word / 图片等，供招聘专家下载。"""

    EXT_ALLOWLIST = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.png', '.jpg', '.jpeg', '.gif', '.zip',
    }
    MAX_SIZE = 10 * 1024 * 1024  # 10MB

    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE,
        related_name='attachments', verbose_name='所属公告',
    )
    file = models.FileField(upload_to='announcements/%Y%m%d/', verbose_name='文件')
    original_name = models.CharField(max_length=255, verbose_name='原始文件名')
    file_size = models.IntegerField(default=0, verbose_name='文件大小(字节)')
    content_type = models.CharField(max_length=128, blank=True, default='', verbose_name='MIME 类型')

    class Meta:
        verbose_name = '公告附件'
        verbose_name_plural = '公告附件'
        ordering = ['-created_at']

    def __str__(self):
        return self.original_name

    @property
    def file_url(self):
        if self.file:
            try:
                return self.file.url
            except Exception:
                return ''
        return ''


class AnnouncementPushRecord(FullAuditModel):
    """制度公告推送记录 — 记录每一次推送批次及通知日志关联。

    - total_count: 本次推送覆盖的用户总数。
    - channel: 推送通道（站内信 / 企微）。
    - context: 扩展字段，存储本次生成的 NotificationLog id 列表，用于统计已读/未读。
    """

    CHANNEL_CHOICES = [
        ('IN_APP', '站内信'),
        ('WECOM', '企微'),
    ]

    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE,
        related_name='push_records', verbose_name='所属公告',
    )
    pushed_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+', verbose_name='推送人',
    )
    total_count = models.PositiveIntegerField(default=0, verbose_name='推送人数')
    channel = models.CharField(
        max_length=16, choices=CHANNEL_CHOICES, default='IN_APP',
        verbose_name='推送通道',
    )
    context = models.JSONField(default=dict, blank=True, verbose_name='扩展字段')

    class Meta:
        verbose_name = '公告推送记录'
        verbose_name_plural = '公告推送记录'
        db_table = 'announcement_push_records'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.announcement.title} · {self.created_at} 推送'

    @property
    def log_ids(self) -> list:
        return (self.context or {}).get('log_ids', [])


class AnnouncementConfig(FullAuditModel):
    """制度公告模块级配置（单例行，pk=1）。

    控制「政策制度」模块是否在工作台启用（总开关），由 HR 及以上在管理后台配置；非 HR 仅可读取。
    - show_on_workbench: 是否在工作台（Dashboard）启用政策制度模块（右侧卡片 + 入口）。

    注意：单条公告具体展示在「工作台卡片」还是「更多 / 快捷入口」，由公告自身的
    show_on_workbench / show_in_more 字段决定（见 Announcement 模型），不在本配置中。
    """

    show_on_workbench = models.BooleanField(default=True, verbose_name='工作台展示')

    class Meta:
        verbose_name = '公告配置'
        verbose_name_plural = '公告配置'

    def __str__(self):
        return f'公告配置(工作台={"开" if self.show_on_workbench else "关"})'

    @classmethod
    def get_or_create_default(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'show_on_workbench': True})
        return obj
