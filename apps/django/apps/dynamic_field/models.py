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
    """同模块字段联动规则。

    action_type 决定联动行为:
      - SHOW / HIDE: 触发字段满足条件时, 显示/隐藏目标字段
      - REQUIRE: 触发字段满足条件时, 强制目标字段必填
      - CASCADE_OPTIONS: 触发字段取值决定目标下拉字段的可选项(级联)
    """

    ACTION_SHOW = 'SHOW'
    ACTION_HIDE = 'HIDE'
    ACTION_REQUIRE = 'REQUIRE'
    ACTION_CASCADE = 'CASCADE_OPTIONS'
    ACTION_CHOICES = [
        (ACTION_SHOW, '显示'),
        (ACTION_HIDE, '隐藏'),
        (ACTION_REQUIRE, '设必填'),
        (ACTION_CASCADE, '级联选项'),
    ]

    OP_EQ = 'EQ'
    OP_NE = 'NE'
    OP_IN = 'IN'
    OP_CHOICES = [
        (OP_EQ, '等于'),
        (OP_NE, '不等于'),
        (OP_IN, '属于'),
    ]

    id = models.CharField(max_length=32, primary_key=True, editable=False, help_text='唯一标识')
    module = models.ForeignKey(FieldModule, on_delete=models.CASCADE, related_name='linkage_rules')
    name = models.CharField(max_length=256, blank=True, default='', help_text='规则名称')
    trigger_field_key = models.CharField(max_length=128, help_text='触发字段 key')
    condition_op = models.CharField(max_length=16, choices=OP_CHOICES, default=OP_EQ)
    condition_value = models.JSONField(default=list, blank=True, help_text='条件值(标量或数组, IN 时为数组)')
    action_type = models.CharField(max_length=32, choices=ACTION_CHOICES, default=ACTION_SHOW)
    target_field_keys = models.JSONField(default=list, blank=True, help_text='受影响字段 key 列表')
    action_config = models.JSONField(default=dict, blank=True, help_text='级联选项映射等附加配置')
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
        return f'{self.module.code}/{self.name or self.trigger_field_key}'
