"""EmailVerificationCode.purpose 默认值 'REGISTER' → 'LOGIN'。

2026-10-18 兵哥：自助注册下线后，邮箱验证码只服务于「邮箱验证码登录」，
故把 purpose 默认值改为 'LOGIN'。仅改默认值（列类型/choices 均未变），
存量行的 purpose 值不动（历史记录原样保留，便于审计追溯）。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_drop_registration_application'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailverificationcode',
            name='purpose',
            field=models.CharField(default='LOGIN', max_length=32, verbose_name='用途'),
        ),
    ]
