from django.db import migrations, models


def merge_user_app_data_scope_into_user_role(apps, schema_editor):
    """合并 user_app_data_scope 表 -> user_roles.app_data_scopes(JSON).

    数据保全(幂等):
      - 对每张 UserAppDataScope 行, 定位目标 UserRoleV2(user_id+role_code+system_code),
        把 management_unit_ids 合并(union + 去重)进 app_data_scopes[app_code];
      - 复制完成后再删表, 绝不丢数据.
    """
    UserRoleV2 = apps.get_model('core', 'UserRoleV2')
    try:
        UserAppDataScope = apps.get_model('core', 'UserAppDataScope')
    except LookupError:
        return

    try:
        rows = list(UserAppDataScope.objects.all())
    except Exception:
        # 表已不存在(幂等重跑场景) -> 跳过复制
        return

    copied = 0
    for s in rows:
        ur, _ = UserRoleV2.objects.get_or_create(
            user_id=s.user_id,
            role_code=s.role_code,
            system_code=s.system_code or 'recruit',
            defaults={'management_unit_ids': None},
        )
        scopes = ur.app_data_scopes or {}
        existing = set(scopes.get(s.app_code) or [])
        existing.update(s.management_unit_ids or [])
        scopes[s.app_code] = sorted(existing)
        ur.app_data_scopes = scopes
        ur.save()
        copied += 1
    print(f'[M-merge] user_app_data_scope -> user_roles.app_data_scopes: copied={copied}')


def reverse_merge(apps, schema_editor):
    """反向: 把 app_data_scopes 拆回 user_app_data_scope 表 (仅用于迁移回滚)."""
    UserRoleV2 = apps.get_model('core', 'UserRoleV2')
    UserAppDataScope = apps.get_model('core', 'UserAppDataScope')
    for ur in UserRoleV2.objects.exclude(app_data_scopes__isnull=True):
        scopes = ur.app_data_scopes or {}
        for app_code, ids in scopes.items():
            UserAppDataScope.objects.update_or_create(
                user_id=ur.user_id, role_code=ur.role_code, app_code=app_code,
                system_code=ur.system_code or 'recruit',
                defaults={'management_unit_ids': ids, 'granted_by_id': ur.granted_by_id},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_remove_managementunit_personnel_scope'),
    ]

    operations = [
        # (a) user_roles 增加 app_data_scopes(JSON, 默认 {})
        migrations.AddField(
            model_name='userrolev2',
            name='app_data_scopes',
            field=models.JSONField(
                blank=True, default=dict, null=True, verbose_name='按应用的数据范围'),
        ),
        # (b) 数据复制: UserAppDataScope -> UserRoleV2.app_data_scopes
        migrations.RunPython(merge_user_app_data_scope_into_user_role, reverse_merge),
        # (c) 删除 user_app_data_scope 表
        migrations.DeleteModel('UserAppDataScope'),
    ]
