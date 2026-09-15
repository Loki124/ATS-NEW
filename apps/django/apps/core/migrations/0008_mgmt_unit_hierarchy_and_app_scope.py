from django.db import migrations, models


def backfill_user_app_data_scope(apps, schema_editor):
    """方案 A(2026-09-15) M1 数据回填 (幂等):

    UserRoleV2.management_unit_ids(全局列表) → UserAppDataScope(app_code='recruit')。
    仅处理非空且非 [] 的记录; 已存在 (user_id, role_code, 'recruit') 则跳过, 不重复插。
    """
    UserRoleV2 = apps.get_model('core', 'UserRoleV2')
    UserAppDataScope = apps.get_model('core', 'UserAppDataScope')

    created = 0
    for ur in UserRoleV2.objects.exclude(management_unit_ids__isnull=True):
        ids = ur.management_unit_ids
        if not ids:  # 空 list / 空值跳过
            continue
        if isinstance(ids, list) and len(ids) == 0:
            continue
        _, was_created = UserAppDataScope.objects.get_or_create(
            user_id=ur.user_id,
            role_code=ur.role_code,
            app_code='recruit',
            defaults={
                'system_code': ur.system_code or 'recruit',
                'management_unit_ids': ids,
                'granted_by_id': ur.granted_by_id,
            },
        )
        if was_created:
            created += 1
    # 打印便于迁移日志核对 (非错误, 仅信息)
    print(f'[M1] backfill user_app_data_scope: created={created}')


def reverse_backfill(apps, schema_editor):
    """reverse_code: 仅清掉本次回填的 app_code='recruit' 行, 不动其它来源数据。"""
    UserAppDataScope = apps.get_model('core', 'UserAppDataScope')
    deleted, _ = UserAppDataScope.objects.filter(app_code='recruit').delete()
    print(f'[M1] reverse backfill user_app_data_scope: deleted={deleted}')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_delete_permission'),
    ]

    operations = [
        # 1. ManagementUnit 加 parent_id(树) + personnel_scope(人员范围谓词)
        migrations.AddField(
            model_name='managementunit',
            name='parent_id',
            field=models.BigIntegerField(blank=True, db_index=True, null=True, verbose_name='上级管理单元ID'),
        ),
        migrations.AddField(
            model_name='managementunit',
            name='personnel_scope',
            field=models.JSONField(blank=True, null=True, verbose_name='人员范围条件(JSON谓词)'),
        ),
        migrations.AddIndex(
            model_name='managementunit',
            index=models.Index(fields=['parent_id'], name='idx_mgmt_unit_parent'),
        ),
        # 2. 新建 UserAppDataScope 关联表(数据范围按应用分组)
        migrations.CreateModel(
            name='UserAppDataScope',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.BigIntegerField(db_index=True, verbose_name='用户ID')),
                ('role_code', models.CharField(max_length=64, verbose_name='角色编码')),
                ('system_code', models.CharField(default='recruit', max_length=32, verbose_name='系统编码')),
                ('app_code', models.CharField(max_length=32, verbose_name='应用/模块编码')),
                ('management_unit_ids', models.JSONField(blank=True, null=True, verbose_name='管理单元ID列表(JSON)')),
                ('granted_by_id', models.BigIntegerField(blank=True, null=True, verbose_name='授权人ID')),
                ('granted_at', models.DateTimeField(auto_now_add=True, verbose_name='授权时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'db_table': 'user_app_data_scope',
                'verbose_name': '用户应用数据范围(V2)',
                'verbose_name_plural': '用户应用数据范围(V2)',
                'constraints': [
                    models.UniqueConstraint(
                        fields=['user_id', 'role_code', 'app_code'],
                        name='uk_user_role_app',
                    ),
                ],
                'indexes': [
                    models.Index(fields=['user_id', 'app_code'], name='idx_uads_user_app'),
                ],
            },
            bases=(models.Model,),
        ),
        # 3. 数据回填(幂等, 可反向)
        migrations.RunPython(backfill_user_app_data_scope, reverse_backfill),
    ]
