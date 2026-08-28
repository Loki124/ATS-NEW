"""T133 v2.9 收敛：ControlRule.strength choices 删「仅提示」枚举。

后端处理一致性确认（services.py:243-247）：硬约束 → 阻断；软约束 → 放行+提示。
原「仅提示」与「软约束」走完全相同的代码路径（均为 warnings 分支），保留会误导用户。

DB 状态：迁移前已查实 29 条 active ControlRule 中 0 条「仅提示」（100% 「硬约束」），
故本次 AlterField 仅修改 choices 元数据，无需数据迁移。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campus_control', '0006_alter_controlrule_unique_together_controlrule_code_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='controlrule',
            name='strength',
            field=models.CharField(
                choices=[('硬约束', '硬约束'), ('软约束', '软约束')],
                default='硬约束',
                max_length=16,
                verbose_name='控制强度',
            ),
        ),
    ]
