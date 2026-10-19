"""动态策略 资源码注册 + 授予 SUPER_ADMIN / ADMIN 角色（2026-10-20）。

数据迁移（无 schema 变更）：
- 把 recruit:dynamic_strategy:{menu:view,list,create,edit,delete} 五条资源注册进
  permission_resources（与 seed_v2_init.RESOURCES 真源对齐，使后续 seed/backfill 一致）；
- 给 SUPER_ADMIN 与 ADMIN 角色写入 role_permission 授权行（ADMIN 是动态策略页
  meta.roles = SUPER_ADMIN_ADMIN 的目标角色之一；SUPER_ADMIN 虽由 is_super_admin bypass，
  但补齐授权行使权限表语义完整）。

幂等：update_or_create，重跑安全。反向迁移清理这五条资源与其角色授权行。
"""
from django.db import migrations


SYSTEM = 'recruit'

CODES = [
    ('recruit:dynamic_strategy:menu:view', '动态策略菜单', 'MENU'),
    ('recruit:dynamic_strategy:list', '动态策略列表', 'BUTTON'),
    ('recruit:dynamic_strategy:create', '创建动态策略', 'BUTTON'),
    ('recruit:dynamic_strategy:edit', '编辑动态策略', 'BUTTON'),
    ('recruit:dynamic_strategy:delete', '删除动态策略', 'BUTTON'),
]

ROLE_CODES = ('SUPER_ADMIN', 'ADMIN')


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    RolePerm = apps.get_model('core', 'RolePermissionV2')

    for code, name, rtype in CODES:
        Resource.objects.update_or_create(
            resource_code=code,
            defaults={
                'system_code': SYSTEM,
                'resource_name': name,
                'resource_type': rtype,
                'module': 'settings',
                'status': 1,
            },
        )

    for role_code in ROLE_CODES:
        for code, _, _ in CODES:
            RolePerm.objects.update_or_create(
                role_code=role_code,
                resource_code=code,
                system_code=SYSTEM,
                defaults={},
            )


def backward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    RolePerm = apps.get_model('core', 'RolePermissionV2')

    code_set = [c[0] for c in CODES]
    RolePerm.objects.filter(
        role_code__in=ROLE_CODES, resource_code__in=code_set, system_code=SYSTEM,
    ).delete()
    Resource.objects.filter(resource_code__in=code_set, system_code=SYSTEM).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0033_mark_disabled_resources'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
