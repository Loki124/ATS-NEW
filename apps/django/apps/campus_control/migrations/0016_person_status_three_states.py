"""2026-10-21 兵哥口径：校招生人员状态收敛为三态（在职 / 待入职 / 离职）。

背景：人员管理（校招生档案）原有五态 —— 在职 / 在途Offer / 在途待入职 / 候选池 / 离职。
按业务口径，后三态中的「在途Offer」「在途待入职」「候选池」**同属「未入职」**，
在人员管理里不再区分，合并为「待入职」；「在途待入职」同时更名为「待入职」。

影响面：
1. `Person.status` 的 choices 收敛为三值（枚举唯一真源：`apps/campus_control/constants.py` 的 STATUS）。
2. 存量数据同步改写：status IN ('在途Offer','在途待入职','候选池') → '待入职'。
   必须同步改写，否则这些人在列表页签里查不到，且核算口径（calc._COUNTED_STATUSES）
   会因状态值对不上而**漏计**（占编数凭空少一截）。
3. 反向迁移不可逆（无法把「待入职」拆回三个旧态），reverse 置 noop。
"""
from django.db import migrations, models

LEGACY_STATUSES = ('在途Offer', '在途待入职', '候选池')


def forwards(apps, schema_editor):
    Person = apps.get_model('campus_control', 'Person')
    Person.objects.filter(status__in=LEGACY_STATUSES).update(status='待入职')


class Migration(migrations.Migration):

    dependencies = [
        ('campus_control', '0015_person_candidate_link'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='status',
            field=models.CharField(
                choices=[('在职', '在职'), ('待入职', '待入职'), ('离职', '离职')],
                db_index=True,
                default='在职',
                max_length=16,
                verbose_name='状态',
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
