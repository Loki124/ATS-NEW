"""Stage Time Limit Rule Models (PRD v4 §11.5)

阶段限时基于规则的动态配置：
- 不同条件不同限时
- 锁定时长（自然日）
- 加时规则（天/人）
- 生效方式：ALL / NEW_ONLY
"""
from django.db import models
from nanoid import generate as nanoid_generate

from apps.common.models import SoftDeleteModel, TimestampedModel
from apps.process.models import ProcessStageLink


def gen_id():
    return nanoid_generate(size=21)


class TimeLimitRule(TimestampedModel, SoftDeleteModel):
    """阶段限时规则

    继承 ``SoftDeleteModel`` 的来由（P0 修复，2026-08-11）
    =====================================================
    本模型原先只继承 ``TimestampedModel``，**没有 deleted_at 字段**，
    但代码库有三处已经按"它有软删"来写：

    1. ``services.calc_time_limit`` 的 ``filter(deleted_at__isnull=True)``
       —— 字段不存在 → 每次调用直接抛 ``FieldError``。而它是
       ``create_application`` / ``advance_application_to_next_stage`` /
       ``jump_application_to_stage`` 三个核心服务的必经之路，等于这三个
       HTTP 端点在生产上必然 500。
    2. ``views.perform_destroy`` 的 ``if hasattr(instance, 'deleted_at')``
       —— 条件恒假 → 分支跳过 → DELETE 返回 204 却什么也没删。
    3. 前端与 API 契约均按"删除后不再出现在列表"设计。

    也就是说软删是**设计意图，只是字段漏了**。修法取"补齐字段"而非
    "删掉这些过滤"：后者会让 DELETE 变成真删（破坏审计可追溯），
    且与全仓 ``FullAuditModel`` 的软删约定分叉。
    """
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
