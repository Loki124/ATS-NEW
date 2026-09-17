"""ManagementUnit 增加按应用(per-app)的独立范围字段 + 成员归属应用 (Plan A Phase 3).

- ManagementUnit.org_scopes: { app_code: OrgScopeNode[] }  各应用 Tab 独立组织范围
- ManagementUnit.data_ranges: { app_code: DataRange }      各应用 Tab 独立数据范围
- ManagementUnitMember.app_code: 成员所属应用 Tab (null=公共), 用于详情抽屉按应用筛选成员

向后兼容: org_scope / data_range 仍作为 'public' 默认切片, scope_resolver 行为不变.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_managementunit_code_description_display_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='managementunit',
            name='org_scopes',
            field=models.JSONField(blank=True, null=True, verbose_name='按应用组织范围(JSON){app_code: OrgScopeNode[]}'),
        ),
        migrations.AddField(
            model_name='managementunit',
            name='data_ranges',
            field=models.JSONField(blank=True, null=True, verbose_name='按应用数据范围(JSON){app_code: DataRange}'),
        ),
        migrations.AddField(
            model_name='managementunitmember',
            name='app_code',
            field=models.CharField(blank=True, db_index=True, max_length=32, null=True, verbose_name='应用编码(成员所属应用 Tab, null=公共)'),
        ),
    ]
