"""2026-10-22：轮岗安排补「校招生档案」人员级关联（nanoid 口径）。

背景：`RotationArrangement.person_id` 是旧口径（BigInteger，语义 = Person.user_id），
而 dev 库里 56 名校招生的 `user_id` **全为空** → 按人定位轮岗安排无口径可用，
「按轮岗状态筛人」只能退化成班级级（会把同班所有人算进去）。

本次新增 `campus_person` FK（Person 主键 nanoid），并按旧口径回填：
    campus_person ← Person WHERE Person.user_id = person_id
回填不覆盖已有值（幂等）。
"""
import django.db.models.deletion
from django.db import migrations, models


def forwards(apps, schema_editor):
    """按旧口径回填：person_id（用户 id）→ campus_person（档案 id）。"""
    Person = apps.get_model('campus_control', 'Person')
    RotationArrangement = apps.get_model('campus_rotation', 'RotationArrangement')
    by_user_id = {
        p.user_id: p.id
        for p in Person.objects.filter(user_id__isnull=False).values('id', 'user_id')
    }
    if not by_user_id:
        return
    for arr in RotationArrangement.objects.filter(
        person_id__isnull=False, campus_person__isnull=True,
    ).iterator():
        target = by_user_id.get(arr.person_id)
        if target:
            arr.campus_person_id = target
            arr.save(update_fields=['campus_person'])


def backwards(apps, schema_editor):
    """反向不回填（数据可由 person_id 重新推导，无需保留）——置空即可。"""
    RotationArrangement = apps.get_model('campus_rotation', 'RotationArrangement')
    RotationArrangement.objects.filter(campus_person__isnull=False).update(campus_person=None)


class Migration(migrations.Migration):

    dependencies = [
        ('campus_rotation', '0013_classroom_class_monitor_rotationarrangement_batch'),
        ('campus_control', '0020_person_batch_person_degree_person_hrbp'),
    ]

    operations = [
        migrations.AddField(
            model_name='rotationarrangement',
            name='campus_person',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='rotation_arrangements',
                to='campus_control.person',
                verbose_name='校招生档案',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
