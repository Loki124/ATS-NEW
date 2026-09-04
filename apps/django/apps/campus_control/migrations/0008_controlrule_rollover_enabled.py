"""v2.10 增量：ControlRule 新增 `rollover_enabled`（月度浮动目标开关）。

迁移策略：AddField（与 v2.9 `0007_alter_controlrule_strength_choices.py` 同模式）。
- default=False：存量行默认未启用浮动 → 与 v2.4 行为完全一致（零回归）。
- 无 RunPython：default 即可满足存量行回填语义。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campus_control', '0007_alter_controlrule_strength_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='controlrule',
            name='rollover_enabled',
            field=models.BooleanField(default=False, verbose_name='启用本月浮动目标'),
        ),
    ]