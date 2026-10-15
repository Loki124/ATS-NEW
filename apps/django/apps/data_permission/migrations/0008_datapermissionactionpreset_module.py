from django.db import migrations, models


class Migration(migrations.Migration):
    """为动作预设包新增「功能模块」字段（module），供前端归属展示与筛选。"""

    dependencies = [
        ('data_permission', '0007_remove_datapermissionrule_priority'),
    ]

    operations = [
        migrations.AddField(
            model_name='datapermissionactionpreset',
            name='module',
            field=models.CharField(
                blank=True, max_length=32, null=True, verbose_name='功能模块'),
        ),
    ]
