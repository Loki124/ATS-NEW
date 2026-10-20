"""S5-10（需求 2-2）：Person 增加 工号 / 班主任 / 班级 三字段。

- employee_id：CharField，空串默认，可空；入职后补录。
- head_teacher：FK→core.User，可空（SET_NULL）。
- class_room：FK→campus_rotation.ClassRoom，可空（SET_NULL）；字符串引用避循环 import。
所有字段均 null/blank=True，不破坏既有数据，迁移安全。
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('campus_control', '0010_person_idx_person_status_bu_school_and_more'),
        ('campus_rotation', '0002_classroom_capacity'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='employee_id',
            field=models.CharField(
                blank=True, db_index=True, default='', max_length=50, verbose_name='工号'
            ),
        ),
        migrations.AddField(
            model_name='person',
            name='head_teacher',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='+', to='core.User', verbose_name='班主任',
            ),
        ),
        migrations.AddField(
            model_name='person',
            name='class_room',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='persons', to='campus_rotation.ClassRoom', verbose_name='班级',
            ),
        ),
    ]
