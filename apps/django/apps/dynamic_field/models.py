from django.db import models

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

    id = models.CharField(max_length=64, primary_key=True)
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
    status = models.CharField(max_length=32, default='active')
    options = models.JSONField(default=list, blank=True, help_text='选项列表 [{value, label}]')

    class Meta:
        db_table = 'dynamic_fields'
        unique_together = [('resource', 'field_key')]
        ordering = ['resource', 'order_index']

    def __str__(self):
        return f'{self.resource}/{self.field_key}'
