"""ManagementUnit 增加「按应用生效开关」字段 (2026-09-19 兵哥需求).

- ManagementUnit.org_scope_enabled: 按应用组织范围是否启用 {app_code: bool}
- ManagementUnit.person_scope_enabled: 按应用人员范围是否启用 {app_code: bool}

语义: 详情弹窗「管理组织范围 / 管理人员范围」区块左侧的 NSwitch 此前是纯本地
ref(假控件, 切了不落库)。本次将其持久化为 per-app 布尔, 缺省 True(未配置即启用,
向后兼容既有数据)。

存储约定: 与 org_scopes/data_ranges 一致, 以 app_code 为 key, 含 'public'。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_renumber_department_codes'),
    ]

    operations = [
        migrations.AddField(
            model_name='managementunit',
            name='org_scope_enabled',
            field=models.JSONField(blank=True, null=True, verbose_name='按应用组织范围启用(JSON){app_code: bool}'),
        ),
        migrations.AddField(
            model_name='managementunit',
            name='person_scope_enabled',
            field=models.JSONField(blank=True, null=True, verbose_name='按应用人员范围启用(JSON){app_code: bool}'),
        ),
    ]
