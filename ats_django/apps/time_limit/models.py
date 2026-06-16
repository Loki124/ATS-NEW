"""Stage Time Limit Rule Models (PRD v4 §11.5)

阶段限时基于规则的动态配置：
- 不同条件不同限时
- 锁定时长（自然日）
- 加时规则（天/人）
- 生效方式：ALL / NEW_ONLY
"""
from django.db import models
from apps.common.models import TimestampedModel
from apps.process.models import ProcessStageLink
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class TimeLimitRule(TimestampedModel):
    """阶段限时规则"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    link = models.ForeignKey(
        ProcessStageLink, on_delete=models.CASCADE,
        related_name='time_limit_rules', verbose_name='流程-阶段关联',
    )
    process_id = models.CharField(max_length=32, db_index=True, verbose_name='流程ID')
    workflow_version = models.CharField(max_length=20, verbose_name='流程版本')

    rule_name = models.CharField(max_length=30, verbose_name='规则名称')
    conditions = models.JSONField(default=list, verbose_name='执行条件', help_text='JSON 数组')

    lock_duration = models.IntegerField(verbose_name='锁定时长（自然日）', help_text='1-365 天')
    extension_per_person = models.IntegerField(default=0, verbose_name='加时规则（天/人）', help_text='0-30 天')

    effective_scope = models.CharField(
        max_length=16, default='NEW_ONLY', verbose_name='生效方式',
        help_text='ALL / NEW_ONLY',
    )
    priority = models.IntegerField(default=0, db_index=True, verbose_name='优先级（列表顺序）')

    enabled = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    created_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='创建人',
    )
    updated_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='更新人',
    )

    class Meta:
        db_table = 'stage_time_limit_rules'
        verbose_name = '阶段限时规则'
        verbose_name_plural = verbose_name
        ordering = ['link', 'priority']

    def __str__(self):
        return f'{self.rule_name} ({self.lock_duration}d)'
