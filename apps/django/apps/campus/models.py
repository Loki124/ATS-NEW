"""校招专属业务模型：校园大使 + 宣讲会 + 模块配置。

这些模型属于「校园招聘」系统专属功能，与社会招聘数据相互隔离：
- recruit_type 硬分区列默认 'campus'（与 Phase 3 基础设施一致）；
- ViewSet 经 ScopeQuerysetMixin 自动按 request.recruit_type 过滤读侧，
  并强制在写侧注入 recruit_type='campus'（防绕过）。
"""
from django.db import models

from apps.common.models import FullAuditModel, UUIDModel
from apps.reason_library.models import RECRUIT_TYPE_CHOICES, RecruitType


class CampusAmbassador(FullAuditModel, UUIDModel):
    """校园大使：各高校的学生大使，承接校招宣传、宣讲会组织与候选人推荐。"""

    class Status(models.TextChoices):
        ACTIVE = 'active', '已激活'
        PENDING = 'pending', '待审核'
        INACTIVE = 'inactive', '已停用'

    school = models.CharField(max_length=64, verbose_name='高校')
    name = models.CharField(max_length=32, verbose_name='大使姓名')
    region = models.CharField(max_length=32, blank=True, default='', verbose_name='区域')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, verbose_name='状态',
    )
    phone = models.CharField(max_length=32, blank=True, default='', verbose_name='联系电话')
    note = models.TextField(blank=True, default='', verbose_name='备注')
    recruit_type = models.CharField(
        max_length=16, choices=RECRUIT_TYPE_CHOICES, default=RecruitType.CAMPUS.value,
        db_index=True, verbose_name='招聘类型',
    )

    class Meta:
        verbose_name = '校园大使'
        verbose_name_plural = '校园大使'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}（{self.school}）'


class CampusSession(FullAuditModel, UUIDModel):
    """宣讲会：校招宣讲排期、场地与线上直播管理。"""

    class SessionType(models.TextChoices):
        OFFLINE = 'offline', '线下'
        ONLINE = 'online', '线上'
        HYBRID = 'hybrid', '线上线下结合'

    class Status(models.TextChoices):
        PLANNED = 'planned', '已排期'
        ONGOING = 'ongoing', '进行中'
        ENDED = 'ended', '已结束'
        CANCELLED = 'cancelled', '已取消'

    title = models.CharField(max_length=128, verbose_name='宣讲会名称')
    school = models.CharField(max_length=64, blank=True, default='', verbose_name='高校')
    session_type = models.CharField(
        max_length=16, choices=SessionType.choices, default=SessionType.OFFLINE, verbose_name='形式',
    )
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    venue = models.CharField(max_length=128, blank=True, default='', verbose_name='场地')
    online_link = models.URLField(blank=True, default='', verbose_name='线上链接')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name='容纳人数')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PLANNED, verbose_name='状态',
    )
    note = models.TextField(blank=True, default='', verbose_name='备注')
    recruit_type = models.CharField(
        max_length=16, choices=RECRUIT_TYPE_CHOICES, default=RecruitType.CAMPUS.value,
        db_index=True, verbose_name='招聘类型',
    )

    class Meta:
        verbose_name = '宣讲会'
        verbose_name_plural = '宣讲会'
        ordering = ['-start_time', '-created_at']

    def __str__(self):
        return self.title


class CampusModuleConfig(FullAuditModel):
    """校招专属模块配置（如校园大使/宣讲会的启用开关）。

    key 唯一（'ambassador' / 'session'），config 为 JSONField 自由 dict，
    与前端 formData 同构（沿用 DemandConfigView 单体配置范式）。
    """

    key = models.CharField(max_length=32, unique=True, verbose_name='配置键')
    config = models.JSONField(default=dict, verbose_name='配置内容')

    class Meta:
        verbose_name = '校招模块配置'
        verbose_name_plural = '校招模块配置'

    def __str__(self):
        return f'CampusModuleConfig[{self.key}]'
