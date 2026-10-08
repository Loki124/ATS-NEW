from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_alter_user_uuid'),
    ]

    operations = [
        # 2026-10-09 (#19): 令牌版本。改密/禁用时 +1 使 outstanding refresh token 失效。
        migrations.AddField(
            model_name='user',
            name='token_version',
            field=models.PositiveIntegerField(
                default=0, db_index=True, verbose_name='令牌版本',
            ),
        ),
    ]
