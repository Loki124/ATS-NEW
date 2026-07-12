# Generated for V2 权限系统 (spec §3.2, T2)
#
# 注意:
# - RoleV2 / UserRoleV2 的 db_table 与 V1 (roles / user_roles) 重名。
#   V1 在 T17 drop_old 之前保留,V1 0001_initial 已创建同名表。
#   此处用 SeparateDatabaseAndState 仅注册 V2 模型状态,跳过 DDL,
#   实际表结构由 V1 表承载;V2 schema 真正生效在 T17 (V1 表 drop 后
#   由独立的 v2_apply_schema 迁移重建)。
# - 其他 5 张表 (permission_resources / permission_templates /
#   role_permission / management_units / tenant_configs) 是 V2 全新表,
#   正常 CreateModel。

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # ---- V1 Role/UserRole → managed = False (让 V2 接管 db_table 命名权) ----
        migrations.AlterModelOptions(
            name='role',
            options={'managed': False, 'verbose_name': '角色', 'verbose_name_plural': '角色'},
        ),
        migrations.AlterModelOptions(
            name='userrole',
            options={'managed': False, 'verbose_name': '用户角色', 'verbose_name_plural': '用户角色'},
        ),

        # ---- V2 全新表 (无 db_table 冲突) ----
        migrations.CreateModel(
            name='ManagementUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('system_code', models.CharField(default='recruit', max_length=32, verbose_name='系统编码')),
                ('unit_name', models.CharField(max_length=64, verbose_name='管理单元名称')),
                ('unit_type', models.CharField(default='org', max_length=20, verbose_name='单元类型')),
                ('org_scope', models.JSONField(blank=True, null=True, verbose_name='组织范围(JSON)')),
                ('include_children', models.SmallIntegerField(default=1, verbose_name='是否包含子级(1是 0否)')),
                ('status', models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '管理单元',
                'verbose_name_plural': '管理单元',
                'db_table': 'management_units',
            },
        ),
        migrations.CreateModel(
            name='PermissionResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('system_code', models.CharField(default='recruit', max_length=32, verbose_name='系统编码')),
                ('resource_code', models.CharField(max_length=128, unique=True, verbose_name='资源编码')),
                ('resource_name', models.CharField(max_length=64, verbose_name='资源名称')),
                ('resource_type', models.CharField(choices=[('MENU', '菜单'), ('BUTTON', '按钮'), ('FIELD', '字段'), ('API', 'API')], max_length=20, verbose_name='资源类型')),
                ('parent_code', models.CharField(blank=True, max_length=128, null=True, verbose_name='父资源编码')),
                ('module', models.CharField(blank=True, max_length=32, null=True, verbose_name='模块')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('status', models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')),
                ('ext_fields', models.JSONField(blank=True, null=True, verbose_name='扩展字段')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '权限资源',
                'verbose_name_plural': '权限资源',
                'db_table': 'permission_resources',
                'indexes': [models.Index(fields=['system_code', 'module'], name='idx_system_module')],
            },
        ),
        migrations.CreateModel(
            name='PermissionTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('system_code', models.CharField(default='recruit', max_length=32, verbose_name='系统编码')),
                ('template_code', models.CharField(max_length=64, unique=True, verbose_name='模板编码')),
                ('template_name', models.CharField(max_length=64, verbose_name='模板名称')),
                ('description', models.CharField(blank=True, max_length=255, null=True, verbose_name='描述')),
                ('is_system', models.SmallIntegerField(default=1, verbose_name='是否系统预置(1是 0否)')),
                ('permission_codes', models.JSONField(default=list, verbose_name='权限码列表(JSON 数组)')),
                ('status', models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '权限模板',
                'verbose_name_plural': '权限模板',
                'db_table': 'permission_templates',
            },
        ),
        migrations.CreateModel(
            name='RolePermissionV2',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role_code', models.CharField(max_length=64, verbose_name='角色编码')),
                ('resource_code', models.CharField(max_length=128, verbose_name='资源编码')),
                ('system_code', models.CharField(max_length=32, verbose_name='系统编码')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '角色资源关联(V2)',
                'verbose_name_plural': '角色资源关联(V2)',
                'db_table': 'role_permission',
                'constraints': [models.UniqueConstraint(fields=('role_code', 'resource_code'), name='uk_role_resource')],
            },
        ),
        migrations.CreateModel(
            name='TenantConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('system_code', models.CharField(max_length=32, verbose_name='系统编码')),
                ('config_key', models.CharField(max_length=64, verbose_name='配置键')),
                ('config_value', models.JSONField(default=dict, verbose_name='配置值(JSON)')),
                ('description', models.CharField(blank=True, max_length=255, null=True, verbose_name='描述')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '租户配置',
                'verbose_name_plural': '租户配置',
                'db_table': 'tenant_configs',
                'constraints': [models.UniqueConstraint(fields=('system_code', 'config_key'), name='uk_system_key')],
            },
        ),

        # ---- V2 重名表: 仅注册 model state,不执行 DDL (等 T17 v2_apply_schema) ----
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='RoleV2',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('system_code', models.CharField(default='recruit', max_length=32, verbose_name='系统编码')),
                        ('role_code', models.CharField(max_length=64, verbose_name='角色编码')),
                        ('role_name', models.CharField(max_length=64, verbose_name='角色名称')),
                        ('template_code', models.CharField(blank=True, max_length=64, null=True, verbose_name='模板编码')),
                        ('default_data_scope_type', models.CharField(blank=True, max_length=32, null=True, verbose_name='默认数据权限范围类型')),
                        ('description', models.CharField(blank=True, max_length=255, null=True, verbose_name='描述')),
                        ('is_system', models.SmallIntegerField(default=0, verbose_name='是否系统预置(1是 0否)')),
                        ('status', models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')),
                        ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                        ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                    ],
                    options={
                        'verbose_name': '角色(V2)',
                        'verbose_name_plural': '角色(V2)',
                        'db_table': 'roles',
                        'constraints': [models.UniqueConstraint(fields=('system_code', 'role_code'), name='uk_system_role')],
                    },
                ),
                migrations.CreateModel(
                    name='UserRoleV2',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('user_id', models.BigIntegerField(verbose_name='用户ID')),
                        ('role_code', models.CharField(max_length=64, verbose_name='角色编码')),
                        ('system_code', models.CharField(default='recruit', max_length=32, verbose_name='系统编码')),
                        ('management_unit_ids', models.JSONField(blank=True, null=True, verbose_name='管理单元ID列表(JSON)')),
                        ('valid_from', models.DateField(blank=True, null=True, verbose_name='生效日期')),
                        ('valid_to', models.DateField(blank=True, null=True, verbose_name='失效日期')),
                        ('granted_by_id', models.BigIntegerField(blank=True, null=True, verbose_name='授权人ID')),
                        ('granted_at', models.DateTimeField(auto_now_add=True, verbose_name='授权时间')),
                        ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                    ],
                    options={
                        'verbose_name': '用户角色(V2)',
                        'verbose_name_plural': '用户角色(V2)',
                        'db_table': 'user_roles',
                        'indexes': [models.Index(fields=['user_id'], name='idx_user_id')],
                        'constraints': [models.UniqueConstraint(fields=('user_id', 'role_code'), name='uk_user_role')],
                    },
                ),
            ],
            database_operations=[],  # 不执行 DDL,T17 时由 v2_apply_schema 创建新表
        ),
    ]