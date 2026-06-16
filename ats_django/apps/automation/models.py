"""Automation Rule Models (PRD v4 §11.3 + 02-feature-spec-automation.md)

自动化规则引擎 - 4 维配置：
1. 触发器 (trigger): 进入阶段/状态变更/评价提交/定时巡检
2. 执行时机 (timing): 立即/延迟/1-15 个工作日
3. 条件 (condition): 子规则组合
4. 动作 (action): 自动推进/跳过/发提醒/入库
"""
from django.db import models
from apps.common.models import TimestampedModel
from apps.process.models import RecruitmentStage, RecruitmentProcess
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class AutomationRule(TimestampedModel):
    """自动化规则"""
    class TriggerType(models.TextChoices):
        STAGE_ENTERED = 'STAGE_ENTERED', '进入阶段'
        STATE_CHANGED = 'STATE_CHANGED', '状态变更'
        EVALUATION_SUBMITTED = 'EVALUATION_SUBMITTED', '评价提交'
        SCHEDULED = 'SCHEDULED', '定时巡检'

    class TriggerTiming(models.TextChoices):
        IMMEDIATE = 'IMMEDIATE', '立即执行'
        DELAY = 'DELAY', '延迟 N 小时'
        WORKING_DAYS = 'WORKING_DAYS', '1-15 个工作日'

    class ConditionLogic(models.TextChoices):
        ALL = 'ALL', '全部满足'
        ANY = 'ANY', '任意满足'

    class ActionType(models.TextChoices):
        AUTO_ADVANCE = 'AUTO_ADVANCE', '自动推进到下一阶段'
        SKIP_TO = 'SKIP_TO', '跳过到指定阶段'
        REMIND = 'REMIND', '发提醒'
        REJECT_TO_POOL = 'REJECT_TO_POOL', '入公共人才库'

    class Priority(models.TextChoices):
        P0 = 'P0', 'P0 - 最高'
        P1 = 'P1', 'P1 - 中'
        P2 = 'P2', 'P2 - 低'

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    name = models.CharField(max_length=50, verbose_name='规则名称')

    process = models.ForeignKey(
        RecruitmentProcess, on_delete=models.CASCADE,
        related_name='automation_rules', verbose_name='所属流程',
    )
    stage = models.ForeignKey(
        RecruitmentStage, on_delete=models.CASCADE,
        related_name='automation_rules', verbose_name='触发现阶段',
    )

    # 触发器
    trigger_type = models.CharField(max_length=32, choices=TriggerType.choices, verbose_name='触发器')
    trigger_timing = models.CharField(max_length=32, choices=TriggerTiming.choices, verbose_name='执行时机')
    trigger_delay_hours = models.IntegerField(null=True, blank=True, verbose_name='延迟小时数')

    # 条件
    condition_logic = models.CharField(
        max_length=8, choices=ConditionLogic.choices,
        default=ConditionLogic.ALL, verbose_name='条件逻辑',
    )
    condition_json = models.JSONField(default=list, verbose_name='子规则')

    # 动作
    action_type = models.CharField(max_length=32, choices=ActionType.choices, verbose_name='动作类型')
    next_stage = models.ForeignKey(
        RecruitmentStage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='目标阶段',
    )
    skip_check = models.BooleanField(default=False, verbose_name='无视下阶段进入条件')

    # 适用范围
    scope_json = models.JSONField(default=dict, verbose_name='适用范围', help_text='{positions, priority, referral_type}')

    # 优先级
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.P1, verbose_name='优先级')

    # 状态
    enabled = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    # 失败率告警
    failure_rate_threshold = models.FloatField(default=0.5, verbose_name='熔断失败率阈值')

    # 审计
    created_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='创建人',
    )
    updated_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='更新人',
    )

    class Meta:
        db_table = 'automation_rules'
        verbose_name = '自动化规则'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['process', 'stage']),
            models.Index(fields=['enabled', 'priority']),
        ]

    def __str__(self):
        return f'[{self.priority}] {self.name} ({self.get_action_type_display()})'


class AutomationLog(TimestampedModel):
    """自动化执行日志"""
    class EvaluateResult(models.TextChoices):
        MATCHED = 'MATCHED', '匹配'
        UNMATCHED = 'UNMATCHED', '不匹配'
        ERROR = 'ERROR', '错误'

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    rule = models.ForeignKey(
        AutomationRule, on_delete=models.CASCADE,
        related_name='logs', verbose_name='规则',
    )
    candidate_id = models.CharField(max_length=32, db_index=True, verbose_name='候选人ID')

    trigger_time = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='触发时间')
    evaluate_result = models.CharField(max_length=16, choices=EvaluateResult.choices, verbose_name='评估结果')
    action_taken = models.CharField(max_length=200, blank=True, verbose_name='实际执行动作')
    skip_reason = models.CharField(max_length=500, blank=True, verbose_name='跳过原因')
    error_message = models.TextField(blank=True, verbose_name='异常信息')
    execution_ms = models.IntegerField(null=True, blank=True, verbose_name='执行耗时（ms）')

    class Meta:
        db_table = 'automation_logs'
        verbose_name = '自动化执行日志'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['rule', 'trigger_time']),
            models.Index(fields=['candidate_id']),
            models.Index(fields=['evaluate_result', 'trigger_time']),
        ]

    def __str__(self):
        return f'Log[{self.rule.name}] {self.evaluate_result}'
