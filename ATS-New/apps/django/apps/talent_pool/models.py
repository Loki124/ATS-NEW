"""Talent Pool Models (PRD v4 §14.7)"""
from django.db import models
from apps.common.models import FullAuditModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class TalentPoolEntry(FullAuditModel):
    """人才库条目 - 候选人在人才库中的条目"""
    class EntrySource(models.TextChoices):
        REJECTED = 'REJECTED', '本流程未通过'
        WITHDRAWN = 'WITHDRAWN', '候选人主动撤回'
        TIMEOUT = 'TIMEOUT', '超时归档'
        ACTIVE_REJECT = 'ACTIVE_REJECT', '主动拒绝入库'
        MANUAL = 'MANUAL', '手动入库'

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        'candidate.Candidate', on_delete=models.PROTECT,
        related_name='talent_pool_entries', verbose_name='候选人',
    )
    source = models.CharField(max_length=16, choices=EntrySource.choices, verbose_name='入库来源')
    source_detail = models.CharField(max_length=200, blank=True, verbose_name='来源详情')

    # 元数据
    last_position = models.ForeignKey(
        'position.Position', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='最近职位',
    )
    last_stage = models.ForeignKey(
        'process.RecruitmentStage', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='最后阶段',
    )

    # 标签
    tags = models.JSONField(default=list, verbose_name='标签')

    # 激活历史
    activated_count = models.IntegerField(default=0, verbose_name='激活次数')
    last_activated_at = models.DateTimeField(null=True, blank=True, verbose_name='最后激活时间')

    is_active = models.BooleanField(default=True, db_index=True, verbose_name='在库')

    class Meta:
        db_table = 'talent_pool_entries'
        verbose_name = '人才库条目'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['source', 'is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.candidate.name} in talent pool ({self.source})'


class TalentPoolTag(FullAuditModel):
    """人才库标签"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    name = models.CharField(max_length=50, unique=True, verbose_name='标签名')
    category = models.CharField(max_length=32, db_index=True, verbose_name='分类',
        help_text='SKILL/INDUSTRY/LEVEL/LOCATION/SOURCE')
    color = models.CharField(max_length=20, default='blue', verbose_name='颜色')

    class Meta:
        db_table = 'talent_pool_tags'
        verbose_name = '人才库标签'
        verbose_name_plural = verbose_name
