"""清理孤儿授权数据（P0-3 / R3 / C5 / ARCH §1.3.2 / PLAN §4.2）。

为什么拆两步（数据清理 → 结构变更）：
  - 结构变更（0024 加 FK）会立即拒绝脏数据，必须先把孤儿行删干净；
  - 数据删除不可逆，单独迁移便于定位与回滚（见 ARCH §5.5.3 备份要求）。

删什么（不可逆）：
  1. user_roles 中 user_id 指向不存在用户（**不按 is_active 过滤** —— 软删用户
     授权须保留，恢复后授权仍在）。
  2. role_permission / user_roles 中 role_code 不在 roles 表（仅 system_code='recruit'）
     的行 —— 孤儿角色（如 test）的授权，永不可能被 has_perm 命中。

不删什么：
  - system_code != 'recruit' 的行（保守，避免误删跨系统数据）。

迁移纪律（项目硬约束）：本迁移只做 `.delete()` / `.values_list()` / `.count()`，
严禁 `.create()`（历史模型无 default=gen_id，会必然失败）。
"""
from django.db import migrations


def purge_orphans(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    User = apps.get_model('core', 'User')
    UserRoleV2 = apps.get_model('core', 'UserRoleV2')
    RoleV2 = apps.get_model('core', 'RoleV2')
    RolePermissionV2 = apps.get_model('core', 'RolePermissionV2')

    # ---- 1. user_roles.user_id → 不存在的用户（不按 is_active 过滤）----
    valid_user_ids = set(
        User.objects.using(db_alias).values_list('id', flat=True)
    )
    orphans = UserRoleV2.objects.using(db_alias).exclude(
        user_id__in=valid_user_ids
    )
    n = orphans.count()
    if n:
        # 留痕：把被删授权明细打印到迁移日志，便于事后对账
        detail = list(orphans.values_list('id', 'user_id', 'role_code')[:5])
        print(f'[P0-3] 删除孤儿用户授权 user_roles: {n} 条，样例={detail}')
        orphans.delete()

    # ---- 2. role_code → 不存在的角色（仅 recruit 系统，保守）----
    valid_role_codes = set(
        RoleV2.objects.using(db_alias)
        .filter(system_code='recruit').values_list('role_code', flat=True)
    )
    bad_roles = UserRoleV2.objects.using(db_alias).exclude(
        role_code__in=valid_role_codes
    )
    n = bad_roles.count()
    if n:
        print(f'[P0-3] 删除孤儿角色用户授权 user_roles: {n} 条')
        bad_roles.delete()

    bad_rp = RolePermissionV2.objects.using(db_alias).exclude(
        role_code__in=valid_role_codes
    )
    n = bad_rp.count()
    if n:
        print(f'[P0-3] 删除孤儿角色权限关联 role_permission: {n} 条')
        bad_rp.delete()


def noop(apps, schema_editor):
    """反迁移：数据已物理删除，不可逆 —— 留空并显式告警（不尝试恢复）。"""
    print('[P0-3] 警告：本迁移的数据清理不可逆，回退不会恢复已删的孤儿授权行。')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_user_token_version'),
    ]

    operations = [
        migrations.RunPython(purge_orphans, noop),
    ]
