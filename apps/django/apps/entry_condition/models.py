"""Entry Condition Rule Models - 阶段进入条件规则（PRD v4 §10）

每条规则独立配置：
- 规则名称
- 规则序号（按启用规则动态计算）
- 状态：ENABLED / DISABLED
- 条件列表（ConditionItem）
- 条件表达式
- 自定义提示内容
"""
from django.db import models
from apps.common.models import TimestampedModel
from apps.process.models import ProcessStageLink
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class EntryConditionRuleStatus(models.TextChoices):
    ENABLED = 'ENABLED', '启用'
    DISABLED = 'DISABLED', '停用'


class ConditionFieldType(models.TextChoices):
    """条件字段类型"""
    STAGE_STATUS = 'STAGE_STATUS', '阶段条件'         # 阶段名称 + 状态
    CANDIDATE = 'CANDIDATE', '候选人'                  # 年龄/学历/经验等
    DEMAND = 'DEMAND', '需求中'                        # 用人经理/上级/BU总裁/VP/职级


class ConditionOperator(models.TextChoices):
    # 通用
    EQ = 'EQ', '='
    NEQ = 'NEQ', '≠'
    GT = 'GT', '>'
    GTE = 'GTE', '≥'
    LT = 'LT', '<'
    LTE = 'LTE', '≤'
    BETWEEN = 'BETWEEN', '介于'
    IN = 'IN', '包含'
    NOT_IN = 'NOT_IN', '不包含'
    IS_EMPTY = 'IS_EMPTY', '为空'
    IS_NOT_EMPTY = 'IS_NOT_EMPTY', '不为空'


class EntryConditionRule(TimestampedModel):
    """进入条件规则

    对应 PRD §10 规则列表中的每条规则
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    link = models.ForeignKey(
        ProcessStageLink, on_delete=models.CASCADE,
        related_name='entry_condition_rules', verbose_name='流程-阶段关联',
    )
    process_id = models.CharField(max_length=32, db_index=True, verbose_name='流程ID')
    workflow_version = models.CharField(max_length=20, verbose_name='流程版本')

    rule_name = models.CharField(max_length=30, verbose_name='规则名称', help_text='限 30 字')
    rule_seq = models.IntegerField(default=1, db_index=True, verbose_name='规则序号', help_text='基于启用规则动态计算')
    status = models.CharField(
        max_length=16, choices=EntryConditionRuleStatus.choices,
        default=EntryConditionRuleStatus.ENABLED, db_index=True, verbose_name='状态',
    )

    # 条件表达式（仅本规则内）
    expression = models.CharField(
        max_length=500, default='1', verbose_name='条件表达式',
        help_text='使用条件序号和逻辑运算符组合，如 (1 AND 2) OR 3',
    )

    # 未满足条件时提示内容
    reject_message = models.CharField(
        max_length=200, blank=True, verbose_name='未满足条件时提示内容',
    )

    # 规则级匹配方式（备用 - 通常使用 expression）
    match_type = models.CharField(max_length=16, default='ALL', verbose_name='匹配方式')

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
        db_table = 'entry_condition_rules'
        verbose_name = '进入条件规则'
        verbose_name_plural = verbose_name
        ordering = ['link', 'rule_seq']
        indexes = [
            models.Index(fields=['link', 'status']),
            models.Index(fields=['link', 'rule_seq']),
        ]

    def __str__(self):
        return f'Rule[{self.rule_seq}] {self.rule_name} ({self.status})'


class ConditionItem(TimestampedModel):
    """条件项 - 规则的原子条件

    字段（field）枚举：
    - 阶段条件：STAGE_NAME + 状态多选
    - 候选人：AGE / GENDER / HIGHEST_EDU / WORK_YEARS / ...
    - 需求中：HIRING_MANAGER / HIRING_MANAGER_SUPER / BU_PRESIDENT / SOLID_VP / DOTTED_VP / DEMAND_LEVEL / DEPARTMENT
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    rule = models.ForeignKey(
        EntryConditionRule, on_delete=models.CASCADE,
        related_name='items', verbose_name='所属规则',
    )

    # 条件项序号（在规则内）
    item_seq = models.IntegerField(default=1, verbose_name='条件序号', help_text='规则内从 1 开始')

    # 条件类型与字段
    condition_type = models.CharField(
        max_length=32, choices=ConditionFieldType.choices,
        verbose_name='条件类型',
    )
    field = models.CharField(max_length=64, verbose_name='字段名')

    # 阶段条件专用
    stage_name = models.CharField(max_length=64, blank=True, verbose_name='关联阶段名')
    stage_statuses = models.JSONField(default=list, blank=True, verbose_name='阶段状态多选')

    # 运算符
    operator = models.CharField(max_length=16, choices=ConditionOperator.choices, verbose_name='运算符')

    # 值（多种类型使用 JSON 存储）
    value = models.JSONField(null=True, blank=True, verbose_name='值')

    # 需求中人员字段专用 - 自动过滤离职人员
    auto_filter_inactive_users = models.BooleanField(default=False, verbose_name='自动过滤离职人员')

    class Meta:
        db_table = 'condition_items'
        verbose_name = '条件项'
        verbose_name_plural = verbose_name
        ordering = ['rule', 'item_seq']

    def __str__(self):
        return f'{self.field} {self.operator} {self.value}'


class EntryConditionLog(TimestampedModel):
    """进入条件评估日志（PRD v4 §10.4）"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    rule = models.ForeignKey(
        EntryConditionRule, on_delete=models.CASCADE,
        related_name='logs', verbose_name='规则',
    )
    candidate_id = models.CharField(max_length=32, db_index=True, verbose_name='候选人ID')
    stage_id = models.CharField(max_length=32, verbose_name='阶段ID')
    link_id = models.CharField(max_length=32, db_index=True, verbose_name='流程-阶段关联ID')

    passed = models.BooleanField(db_index=True, verbose_name='是否通过')
    reject_message = models.CharField(max_length=500, blank=True, verbose_name='未满足提示')
    snapshot = models.JSONField(default=dict, blank=True, verbose_name='评估快照')

    class Meta:
        db_table = 'entry_condition_logs'
        verbose_name = '进入条件评估日志'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['rule', 'created_at']),
            models.Index(fields=['candidate_id', 'link_id']),
        ]
