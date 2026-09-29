"""统一规则引擎 —— 四核心模型 + 枚举（Phase 0 脚手架）。

设计依据：docs/rule-engine/UNIFIED_RULE_ENGINE_DESIGN.md §2.2 / §2.3 / §2.4 / §2.5 / §7.1。

所有模型继承（FullAuditModel, UUIDModel）：
- FullAuditModel：时间戳(created_at/updated_at) + 软删(deleted_at) + created_by/updated_by
- UUIDModel：nanoid(size=21) 主键，save() 自动生成

Phase 0 边界：
- 仅定义数据模型与枚举，不实现任何业务逻辑；求值/派发在 services.py。
- 不建立任何外键指向现有业务表（流程/阶段/候选人等），避免耦合现网调用方。
"""
from django.db import models

from apps.common.models import FullAuditModel, UUIDModel


# ---------------------------------------------------------------------------
# 枚举（统一三大规则族 / 触发 / 动作 / 运算符 / 条件类型 / 优先级 / 状态 / 结果）
# 全部用 models.TextChoices，数据库存值与枚举名一致（如 'TCA' / 'P0'）。
# ---------------------------------------------------------------------------

class RuleCategory(models.TextChoices):
    """规则族：TCA 触发-条件-动作 / CONSTRAINT 约束校验 / POLICY 访问控制。"""
    TCA = 'TCA', '触发-条件-动作'
    CONSTRAINT = 'CONSTRAINT', '约束校验'
    POLICY = 'POLICY', '访问控制'


class UnifiedTriggerType(models.TextChoices):
    """统一触发类型（§2.4）。"""
    STAGE_ENTERED = 'STAGE_ENTERED', '进入阶段'
    STATE_CHANGED = 'STATE_CHANGED', '状态变更'
    EVALUATION_SUBMITTED = 'EVALUATION_SUBMITTED', '评价提交'
    SCHEDULED = 'SCHEDULED', '定时巡检'
    STAGE_DWELL_TIMEOUT = 'STAGE_DWELL_TIMEOUT', '阶段停留超时'
    OFFER_SUBMITTED = 'OFFER_SUBMITTED', '提交 Offer'
    BUSINESS_EVENT = 'BUSINESS_EVENT', '业务事件'


class UnifiedActionType(models.TextChoices):
    """统一动作类型（§2.5）。具体执行器在后续 Phase 实现。"""
    AUTO_ADVANCE = 'AUTO_ADVANCE', '自动推进'
    SKIP_TO = 'SKIP_TO', '跳到指定阶段'
    REMIND = 'REMIND', '发提醒'
    REJECT_TO_POOL = 'REJECT_TO_POOL', '入公共人才库'
    ALLOW = 'ALLOW', '放行'
    REJECT = 'REJECT', '拦截'
    LOCK = 'LOCK', '锁定阶段'
    UNLOCK = 'UNLOCK', '解锁'
    BLOCK_HARD = 'BLOCK_HARD', '硬约束拦截'
    BLOCK_SOFT = 'BLOCK_SOFT', '软约束提示'
    ASSIGN_HANDLER = 'ASSIGN_HANDLER', '指派处理人'
    SET_PERMISSION = 'SET_PERMISSION', '设置字段权限'


class UnifiedOperator(models.TextChoices):
    """统一运算符（14 种，§2.3 + 指标层扩展）。

    2026-09-29 扩展：新增 CONTAINS / NOT_CONTAINS / REGEX_MATCH 三种字符串运算，
    供字符串型指标做「包含关键词 / 正则匹配」类规则（真实实现，非展示占位）。
    """
    EQ = 'EQ', '等于'
    NEQ = 'NEQ', '不等于'
    GT = 'GT', '大于'
    GTE = 'GTE', '大于等于'
    LT = 'LT', '小于'
    LTE = 'LTE', '小于等于'
    BETWEEN = 'BETWEEN', '区间'
    IN = 'IN', '属于集合'
    NOT_IN = 'NOT_IN', '不属于集合'
    IS_EMPTY = 'IS_EMPTY', '为空'
    IS_NOT_EMPTY = 'IS_NOT_EMPTY', '不为空'
    CONTAINS = 'CONTAINS', '包含'
    NOT_CONTAINS = 'NOT_CONTAINS', '不包含'
    REGEX_MATCH = 'REGEX_MATCH', '正则匹配'


class ConditionType(models.TextChoices):
    """条件类型（§2.2.1）。"""
    STAGE_STATUS = 'STAGE_STATUS', '阶段状态'
    CANDIDATE = 'CANDIDATE', '候选人'
    DEMAND = 'DEMAND', '需求'
    CUSTOM = 'CUSTOM', '自定义'


class Priority(models.TextChoices):
    """优先级（§2.7）。P0 > P1 > P2。"""
    P0 = 'P0', 'P0-最高'
    P1 = 'P1', 'P1-中'
    P2 = 'P2', 'P2-低'


class RuleStatus(models.TextChoices):
    """规则启用状态（§2.7）。"""
    ENABLED = 'ENABLED', '启用'
    DISABLED = 'DISABLED', '停用'


class EvaluateResult(models.TextChoices):
    """执行结果（§2.2.1）。"""
    MATCHED = 'MATCHED', '命中'
    UNMATCHED = 'UNMATCHED', '未命中'
    ERROR = 'ERROR', '错误'
    ALLOWED = 'ALLOWED', '放行'
    REJECTED = 'REJECTED', '拦截'
    BLOCKED = 'BLOCKED', '阻塞'
    SKIPPED = 'SKIPPED', '跳过'
    LOCKED = 'LOCKED', '已锁定'


class ConditionLogic(models.TextChoices):
    """条件组合逻辑：无 condition_expression 时兜底（ALL=全部 / ANY=任一）。"""
    ALL = 'ALL', '全部满足'
    ANY = 'ANY', '任一满足'


# ---------------------------------------------------------------------------
# 模型
# ---------------------------------------------------------------------------

class Rule(FullAuditModel, UUIDModel):
    """统一规则主表（rule_engine_rules）。

    收敛所有家族的「规则头」，详见 §2.2.1。Phase 0 仅建模，不含执行逻辑。
    """
    name = models.CharField(max_length=50, verbose_name='规则名称')
    category = models.CharField(
        max_length=16, choices=RuleCategory.choices,
        default=RuleCategory.TCA, verbose_name='规则族',
    )
    source_app = models.CharField(
        max_length=64, blank=True, default='',
        verbose_name='来源 app', help_text='automation/entry_condition/time_limit/campus_control/mou/field_acl/process',
    )
    # Phase 2（2026-08-31）：双写迁移链路。legacy_id/legacy_model 标记该统一规则由哪条
    # legacy 记录镜像而来，bridge.sync_automation_rule_to_unified 以 (source_app, legacy_id)
    # 做幂等 upsert。仅新增字段，不动现有字段与现网调用方。
    legacy_id = models.CharField(
        max_length=64, blank=True, default='', db_index=True,
        verbose_name='来源记录 ID', help_text='legacy 表主键，如 automation.AutomationRule.id',
    )
    legacy_model = models.CharField(
        max_length=128, blank=True, default='',
        verbose_name='来源模型', help_text='legacy app.Model 路径，如 automation.AutomationRule',
    )
    trigger_type = models.CharField(
        max_length=32, choices=UnifiedTriggerType.choices, verbose_name='触发类型',
    )
    trigger_timing = models.CharField(
        max_length=32, null=True, blank=True, verbose_name='执行时机',
    )
    trigger_delay_hours = models.IntegerField(null=True, blank=True, verbose_name='延迟小时')
    trigger_delay_working_days = models.IntegerField(
        null=True, blank=True, verbose_name='延迟工作日',
    )
    scope_json = models.JSONField(default=dict, verbose_name='适用范围',
                                  help_text='标准 scope 结构见 §2.6')
    priority = models.CharField(
        max_length=4, choices=Priority.choices,
        default=Priority.P1, verbose_name='优先级',
    )
    priority_rank = models.IntegerField(default=0, verbose_name='优先级细排')
    status = models.CharField(
        max_length=16, choices=RuleStatus.choices,
        default=RuleStatus.ENABLED, verbose_name='状态',
    )
    enabled = models.BooleanField(default=True, verbose_name='启用开关')
    failure_rate_threshold = models.FloatField(
        default=0.5, verbose_name='熔断失败率阈值',
    )
    condition_expression = models.CharField(
        max_length=500, blank=True, default='', verbose_name='条件表达式',
        help_text='(1 AND 2) OR 3，引用 Condition.seq',
    )
    condition_logic = models.CharField(
        max_length=8, choices=ConditionLogic.choices,
        default=ConditionLogic.ALL, verbose_name='条件逻辑（兜底）',
    )
    config_json = models.JSONField(
        default=dict, verbose_name='家族专属逃逸字段',
    )

    class Meta:
        db_table = 'rule_engine_rules'
        verbose_name = '统一规则'
        verbose_name_plural = '统一规则'
        ordering = ['priority', 'priority_rank']
        indexes = [
            models.Index(fields=['source_app', 'legacy_id'], name='rule_src_legacy'),
        ]

    def __str__(self):
        return f'{self.name}({self.category})'

    @property
    def ordered_conditions(self):
        """按 seq 升序的条件项（供 ConditionEvaluator 遍历）。"""
        return self.conditions.all().order_by('seq')

    @property
    def ordered_actions(self):
        """按 seq 升序的动作项（供 ActionExecutorRegistry 遍历）。"""
        return self.actions.all().order_by('seq')


class Condition(FullAuditModel, UUIDModel):
    """统一条件项（rule_engine_conditions），详见 §2.2.1。"""
    rule = models.ForeignKey(
        Rule, on_delete=models.CASCADE,
        related_name='conditions', verbose_name='所属规则',
    )
    seq = models.IntegerField(verbose_name='规则内序号', help_text='从 1 起，供 condition_expression 引用')
    condition_type = models.CharField(
        max_length=16, choices=ConditionType.choices,
        default=ConditionType.CUSTOM, verbose_name='条件类型',
    )
    field = models.CharField(max_length=64, verbose_name='字段名')
    operator = models.CharField(
        max_length=16, choices=UnifiedOperator.choices, verbose_name='运算符',
    )
    value = models.JSONField(null=True, blank=True, verbose_name='比较值')
    stage_name = models.CharField(max_length=64, null=True, blank=True, verbose_name='阶段名')
    stage_statuses = models.JSONField(null=True, blank=True, verbose_name='阶段状态集合')
    auto_filter_inactive_users = models.BooleanField(
        default=False, verbose_name='自动过滤停用人员',
    )
    meta_json = models.JSONField(default=dict, verbose_name='扩展（BETWEEN 的 min/max 等）')

    class Meta:
        db_table = 'rule_engine_conditions'
        verbose_name = '统一条件项'
        verbose_name_plural = '统一条件项'
        ordering = ['seq']
        unique_together = [('rule', 'seq')]

    def __str__(self):
        return f'#{self.seq} {self.field} {self.operator}'


class Action(FullAuditModel, UUIDModel):
    """统一动作项（rule_engine_actions），详见 §2.2.1。"""
    rule = models.ForeignKey(
        Rule, on_delete=models.CASCADE,
        related_name='actions', verbose_name='所属规则',
    )
    seq = models.IntegerField(verbose_name='执行顺序')
    action_type = models.CharField(
        max_length=32, choices=UnifiedActionType.choices, verbose_name='动作类型',
    )
    params_json = models.JSONField(default=dict, verbose_name='动作参数')
    enabled = models.BooleanField(default=True, verbose_name='动作开关')

    class Meta:
        db_table = 'rule_engine_actions'
        verbose_name = '统一动作项'
        verbose_name_plural = '统一动作项'
        ordering = ['seq']

    def __str__(self):
        return f'#{self.seq} {self.action_type}'


class RuleExecutionLog(FullAuditModel, UUIDModel):
    """统一执行日志（rule_engine_execution_logs），替代分散的 *Log，详见 §2.2.1 / §4.4。"""
    rule = models.ForeignKey(
        Rule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='execution_logs', verbose_name='来源规则',
    )
    rule_category = models.CharField(
        max_length=16, choices=RuleCategory.choices, verbose_name='规则族（冗余）',
    )
    trigger_type = models.CharField(max_length=32, verbose_name='触发类型')
    candidate_id = models.CharField(max_length=64, null=True, blank=True, verbose_name='候选人')
    application_id = models.CharField(max_length=64, null=True, blank=True, verbose_name='应聘')
    stage_id = models.CharField(max_length=64, null=True, blank=True, verbose_name='阶段')
    link_id = models.CharField(max_length=64, null=True, blank=True, verbose_name='阶段链接')
    process_id = models.CharField(max_length=64, null=True, blank=True, verbose_name='流程')
    evaluate_result = models.CharField(
        max_length=16, choices=EvaluateResult.choices, verbose_name='执行结果',
    )
    action_taken = models.CharField(max_length=200, blank=True, default='', verbose_name='实际动作摘要')
    action_type = models.CharField(max_length=64, blank=True, default='', verbose_name='执行动作类型')
    skip_reason = models.CharField(max_length=200, null=True, blank=True, verbose_name='跳过原因')
    error_message = models.TextField(null=True, blank=True, verbose_name='异常信息')
    execution_ms = models.IntegerField(null=True, blank=True, verbose_name='耗时(ms)')
    actor_id = models.CharField(max_length=64, null=True, blank=True, verbose_name='触发人')
    triggered_at = models.DateTimeField(auto_now_add=True, verbose_name='触发时间', db_index=True)

    class Meta:
        db_table = 'rule_engine_execution_logs'
        verbose_name = '统一执行日志'
        verbose_name_plural = '统一执行日志'
        ordering = ['-triggered_at']

    def __str__(self):
        return f'{self.rule_category}/{self.evaluate_result}@{self.triggered_at}'
