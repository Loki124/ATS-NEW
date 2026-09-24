# 2026-09-24 (兵哥): 新增「人员 / 部门」字段类型 — 仅扩展 field_type choices,
# 存量数据零迁移 (原值不变)。选项来源由 options_source 动态解析
# (internal_user / external_user / organization), 见 models.resolve_options_source。

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_field', '0016_alter_dynamicfield_field_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dynamicfield',
            name='field_type',
            field=models.CharField(choices=[('TEXT', '文本'), ('NUMBER', '数字'), ('DATE', '单点日期'), ('DATE_RANGE', '日期范围'), ('SELECT', '单选'), ('MULTISELECT', '多选'), ('BOOLEAN', '布尔'), ('ATTACHMENT', '附件'), ('ID_CARD', '身份证'), ('BANK_CARD', '银行卡'), ('PHONE', '电话'), ('EMAIL', '邮箱'), ('URL', 'URL'), ('LIST_SINGLE', '列表单选'), ('LIST_MULTI', '列表多选'), ('CONFIRM', '确认题'), ('MULTILINE_TEXT', '多行文本'), ('ADDRESS', '地址'), ('REGION', '行政区划'), ('COMPOSITE', '组合字段'), ('RICH_TEXT', '富文本'), ('PERSON', '人员'), ('DEPARTMENT', '部门')], default='TEXT', max_length=32),
        ),
    ]
