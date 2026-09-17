"""ManagementUnit 增加「人员数据范围」字段 (2026-09-17 收敛需求).

- ManagementUnit.person_data_range: 公共(public)人员数据范围 JSON
- ManagementUnit.person_data_ranges: 按应用(person_data_ranges[app])人员数据范围 JSON

语义: 管理单元「可以看哪些人员(创建者)的数据」——
经 scope_resolver 编译为 created_by__department_id__in, 与组织数据范围
(department_id__in) 独立、二者以 AND 并入单元可见性。

向后兼容: org/data_range 与 org_scopes/data_ranges 行为不变.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_managementunit_per_app_scopes'),
    ]

    operations = [
        migrations.AddField(
            model_name='managementunit',
            name='person_data_range',
            field=models.JSONField(blank=True, null=True, verbose_name='人员数据范围(JSON)'),
        ),
        migrations.AddField(
            model_name='managementunit',
            name='person_data_ranges',
            field=models.JSONField(blank=True, null=True, verbose_name='按应用人员数据范围(JSON){app_code: DataRange}'),
        ),
    ]
