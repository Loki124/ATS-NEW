from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('campus_rotation', '0002_classroom_capacity'),
    ]

    operations = [
        # S5-11（需求 2-3）：删除个人档案「班长」字段。
        # 仅 RemoveField，不涉及数据迁移；生产落库前须先备份
        # `campus_rotation_class_rooms` 全表（见 ENGINGEERING_RULES §13 备份纪律）。
        migrations.RemoveField(
            model_name='classroom',
            name='class_monitor',
        ),
    ]
