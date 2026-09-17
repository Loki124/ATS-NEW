"""ManagementUnit 新增 编码/说明/显示顺序 字段 —— 北森图1 列表列对齐 (Plan A Phase 1).

- code: 编码 (列表「编码」列, db_index 便于按编码检索)
- description: 说明 (列表「说明」列, 长文本)
- display_order: 显示顺序 (列表按此升序排序)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_management_unit_data_range'),
    ]

    operations = [
        migrations.AddField(
            model_name='managementunit',
            name='code',
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True, verbose_name='编码'),
        ),
        migrations.AddField(
            model_name='managementunit',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='说明'),
        ),
        migrations.AddField(
            model_name='managementunit',
            name='display_order',
            field=models.IntegerField(db_index=True, default=0, verbose_name='显示顺序'),
        ),
    ]
