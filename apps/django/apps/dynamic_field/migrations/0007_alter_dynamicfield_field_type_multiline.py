from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_field', '0006_dynamicfield_confirmation_content_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dynamicfield',
            name='field_type',
            field=models.CharField(
                choices=[
                    ('TEXT', '文本'),
                    ('NUMBER', '数字'),
                    ('DATE', '日期'),
                    ('SELECT', '单选'),
                    ('MULTISELECT', '多选'),
                    ('BOOLEAN', '布尔'),
                    ('ATTACHMENT', '附件'),
                    ('ID_CARD', '身份证'),
                    ('BANK_CARD', '银行卡'),
                    ('PHONE', '手机号'),
                    ('EMAIL', '邮箱'),
                    ('LIST_SINGLE', '列表单选'),
                    ('LIST_MULTI', '列表多选'),
                    ('CONFIRM', '确认题'),
                    ('MULTILINE_TEXT', '多行文本'),
                ],
                default='TEXT',
                max_length=32,
            ),
        ),
    ]
