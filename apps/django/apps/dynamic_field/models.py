from django.db import models
from nanoid import generate as nanoid_generate

from apps.common.models import TimestampedModel, SoftDeleteModel


class DynamicField(TimestampedModel, SoftDeleteModel):
    """动态字段定义 — 允许管理员为不同 resource (Candidate/Position等) 自定义字段"""

    class FieldType(models.TextChoices):
        TEXT = 'TEXT', '文本'
        NUMBER = 'NUMBER', '数字'
        DATE = 'DATE', '日期'
        SELECT = 'SELECT', '单选'
        MULTISELECT = 'MULTISELECT', '多选'
        BOOLEAN = 'BOOLEAN', '布尔'
        # 2026-09-08 新增专用类型
        ATTACHMENT = 'ATTACHMENT', '附件'
        ID_CARD = 'ID_CARD', '身份证'
        BANK_CARD = 'BANK_CARD', '银行卡'
        PHONE = 'PHONE', '手机号'
        EMAIL = 'EMAIL', '邮箱'

    # 需要选项配置(下拉)的字段类型
    OPTION_TYPES = [FieldType.SELECT, FieldType.MULTISELECT]

    id = models.CharField(
        max_length=32, primary_key=True, editable=False, help_text='唯一标识'
    )
    resource = models.CharField(max_length=128, db_index=True, help_text='资源类型 (Candidate/Position/...)')
    field_key = models.CharField(max_length=128, help_text='字段 key (snake_case)')
    label = models.CharField(max_length=256, help_text='显示名称')
    field_type = models.CharField(max_length=32, choices=FieldType.choices, default=FieldType.TEXT)
    is_required = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    placeholder = models.CharField(max_length=512, blank=True, default='')
    help_text = models.CharField(max_length=512, blank=True, default='')
    default_value = models.CharField(max_length=512, blank=True, default='')
    validation = models.JSONField(default=dict, blank=True, help_text='校验规则 JSON')
    order_index = models.IntegerField(default=0)
    group_name = models.CharField(max_length=128, blank=True, default='')
    # 2026-09-08: 模块(父)/分组(子) 配置化, 字段新增/编辑时可直接下拉选择
    module = models.ForeignKey(
        'FieldModule', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fields', help_text='归属模块(可配置)',
    )
    group = models.ForeignKey(
        'FieldGroup', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fields', help_text='字段分组(可配置)',
    )
    status = models.CharField(max_length=32, default='active')
    options = models.JSONField(default=list, blank=True, help_text='选项列表 [{value, label}]')

    class Meta:
        db_table = 'dynamic_fields'
        unique_together = [('resource', 'field_key')]
        ordering = ['resource', 'order_index']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.resource}/{self.field_key}'


class FieldModule(TimestampedModel, SoftDeleteModel):
    """字段模块(父级) — 可配置, 字段归属某个模块。

    例: resource=Candidate, module=「候选人信息」「教育经历」。
    """

    id = models.CharField(max_length=32, primary_key=True, editable=False, help_text='唯一标识')
    resource = models.CharField(max_length=128, db_index=True, help_text='资源类型 (Candidate/Position/...)')
    code = models.CharField(max_length=128, help_text='模块 code (snake_case)')
    name = models.CharField(max_length=256, help_text='模块显示名称')
    description = models.CharField(max_length=512, blank=True, default='')
    order_index = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'dynamic_field_modules'
        unique_together = [('resource', 'code')]
        ordering = ['resource', 'order_index']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.resource}/{self.code}'


class FieldGroup(TimestampedModel, SoftDeleteModel):
    """字段分组(子级, 隶属于模块) — 字段新增/编辑时可直接下拉选择。"""

    id = models.CharField(max_length=32, primary_key=True, editable=False, help_text='唯一标识')
    module = models.ForeignKey(FieldModule, on_delete=models.CASCADE, related_name='groups')
    code = models.CharField(max_length=128, help_text='分组 code (snake_case)')
    name = models.CharField(max_length=256, help_text='分组显示名称')
    order_index = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'dynamic_field_groups'
        unique_together = [('module', 'code')]
        ordering = ['module', 'order_index']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.module.code}/{self.code}'


class FieldLinkageRule(TimestampedModel, SoftDeleteModel):
    """同模块字段联动规则(多条件 + 多动作)。

    参考设计: 条件区域支持「满足全部/满足任一」; 一条条件 = 字段 + 操作符 + 值;
    动作区域支持多条, 每条 = 目标字段 + 动作类型 + 值 + 是否只读。

    condition_mode: 多条件之间的组合方式
    conditions: [{field_key, op, value}]
    actions:    [{target_field_key, action_type, value, read_only}]
    """

    class ConditionMode(models.TextChoices):
        ALL = 'ALL', '满足以下所有条件'
        ANY = 'ANY', '满足以下任一条件'

    class ConditionOp(models.TextChoices):
        EQ = 'EQ', '等于'
        NE = 'NE', '不等于'
        IN = 'IN', '包含'
        NOT_IN = 'NOT_IN', '不包含'
        GT = 'GT', '大于'
        LT = 'LT', '小于'
        GTE = 'GTE', '大于等于'
        LTE = 'LTE', '小于等于'
        CONTAINS = 'CONTAINS', '包含文本'

    class ActionType(models.TextChoices):
        SHOW = 'SHOW', '显示'
        HIDE = 'HIDE', '隐藏'
        REQUIRE = 'REQUIRE', '设必填'
        SET_VALUE = 'SET_VALUE', '赋值'
        READONLY = 'READONLY', '只读'
        CASCADE_OPTIONS = 'CASCADE_OPTIONS', '级联选项'

    id = models.CharField(max_length=32, primary_key=True, editable=False, help_text='唯一标识')
    module = models.ForeignKey(FieldModule, on_delete=models.CASCADE, related_name='linkage_rules')
    name = models.CharField(max_length=256, blank=True, default='', help_text='规则名称')
    condition_mode = models.CharField(
        max_length=16, choices=ConditionMode.choices, default=ConditionMode.ALL,
        help_text='多条件组合方式',
    )
    conditions = models.JSONField(
        default=list, blank=True,
        help_text='条件列表 [{field_key, op, value}]',
    )
    actions = models.JSONField(
        default=list, blank=True,
        help_text='动作列表 [{target_field_key, action_type, value, read_only}]',
    )
    order_index = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'dynamic_field_linkage_rules'
        ordering = ['module', 'order_index']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.module.code}/{self.name or "未命名规则"}'
