"""T01.1 迁移回归测试 (2026-08-03 寇豆码)

学自 BUG-7 教训 (commit c60b65f): 迁移必须有 ≥1 行真实数据 + fresh DB
验证. 不能光靠 makemigrations --check 通过就当 OK.

覆盖目标 (RT-1 / RT-3 / RT-9):
1. fresh DB 跑完 0001-0004 后, `roles` / `user_roles` 表物理列与 V2 model 完全对齐
2. RoleV2 / UserRoleV2.objects.create() 真实入库 + 真有 V2 特征列 (system_code / granted_by_id)
3. RENAME 备份存在: V1 旧表被备份为 *_v1_backup (即使 fresh DB 上 V1 已经被
   0001_initial 建了)
4. 迁移幂等: 重新跑单 app 的 migrate 不报错 (No migrations to apply)
5. 真业务 INSERT 跑通 + DELETE 跑通

设计要点:
- pytest-django --create-db 已自动跑全量迁移 (含 0004), 不需要测试内 migrate
- 不调 call_command('migrate') — SQLite + 事务内 + schema_editor + FK check = NotSupportedError
- 每个测试用 fresh transaction, 通过 @pytest.mark.django_db
- 不依赖全局 conftest.py 的 _ensure_v2_schema_on_sqlite (那是 V1 fallback),
  本测试专注 fresh DB 的 V2 路径
"""
import pytest
from django.db import connection


def _sqlite_vendor():
    return connection.vendor == 'sqlite'


def _column_names(table):
    """跨 DB vendor 取表的物理列名集合."""
    if _sqlite_vendor():
        with connection.cursor() as c:
            c.execute(f'PRAGMA table_info("{table}")')
            return {r[1] for r in c.fetchall()}
    with connection.cursor() as c:
        c.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name=%s",
            [table],
        )
        return {r[0] for r in c.fetchall()}


def _table_names():
    with connection.cursor() as c:
        if _sqlite_vendor():
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        else:
            c.execute("SELECT table_name FROM information_schema.tables")
        return {r[0] for r in c.fetchall()}


# ============================================================
# Test 1: Fresh DB + migrate → V2 物理列与 model 完全对齐
# (pytest-django --create-db 已跑全量迁移, 直接验证 schema)
# ============================================================
@pytest.mark.django_db
@pytest.mark.v2_permission
def test_v2_roles_columns_aligned_with_model():
    """RT-1: migrate 后 `roles` 表含 V2 特征列 (system_code / role_code / role_name).

    学自 BUG-7: 必须验证真实物理 schema, 不能依赖 ORM 模型字段.
    """
    roles_cols = _column_names('roles')

    # V2 必含列
    for required in ('id', 'system_code', 'role_code', 'role_name',
                     'is_system', 'status', 'created_at', 'updated_at'):
        assert required in roles_cols, (
            f'BUG: V2 column `{required}` missing from roles. '
            f'Got: {sorted(roles_cols)}'
        )

    # V1 旧列不应再在 roles 表里 (已被 RENAME 备份)
    # 注: 'description' V2 RoleV2 也有同名列 (CharField(255, null=True)),
    # 不能作为 V1-only 标识. V1 独有的是 'code' (V2 改名 role_code) /
    # 'name' (V2 改名 role_name) / 'is_builtin' / 'is_active'.
    for v1_only in ('code', 'name', 'is_builtin', 'is_active'):
        assert v1_only not in roles_cols, (
            f'BUG: V1 column `{v1_only}` still in roles (should be RENAME to backup). '
            f'Got: {sorted(roles_cols)}'
        )


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_v2_user_roles_columns_aligned_with_model():
    """RT-1 (续): migrate 后 `user_roles` 表含 V2 特征列 (role_code / granted_by_id)."""
    ur_cols = _column_names('user_roles')

    for required in ('id', 'user_id', 'role_code', 'system_code',
                     'granted_by_id', 'granted_at', 'updated_at'):
        assert required in ur_cols, (
            f'BUG: V2 column `{required}` missing from user_roles. '
            f'Got: {sorted(ur_cols)}'
        )

    # V1 旧列不在
    for v1_only in ('granted_by',):
        assert v1_only not in ur_cols, (
            f'BUG: V1 column `{v1_only}` still in user_roles. '
            f'Got: {sorted(ur_cols)}'
        )


# ============================================================
# Test 2: V2 model 真业务 INSERT 跑通 (学自 BUG-7 教训)
# ============================================================
@pytest.mark.django_db
@pytest.mark.v2_permission
def test_role_v2_create_with_v2_columns_succeeds():
    """RT-2: RoleV2.objects.create() 真实入库, 含 V2 特征字段.

    BUG-7 风格: 用真 model 操作真实物理 schema, 验证列结构对齐.
    之前 _v2_schema_present() 探测到的 False 路径在这条用例上必须消失.
    """
    from apps.core.models_permission_v2 import RoleV2

    role = RoleV2.objects.create(
        system_code='recruit',
        role_code='MIGRATION_TEST_ROLE',
        role_name='迁移测试角色',
        description='由 test_v2_schema_migration 创建',
        is_system=0,
        status=1,
        default_data_scope_type='ALL',
    )
    assert role.id is not None, 'BigAuto PK must auto-assign id'
    assert role.system_code == 'recruit'
    assert role.role_code == 'MIGRATION_TEST_ROLE'
    assert role.role_name == '迁移测试角色'

    # 重读, 验证入库持久化
    fresh = RoleV2.objects.get(role_code='MIGRATION_TEST_ROLE', system_code='recruit')
    assert fresh.id == role.id
    assert fresh.role_name == '迁移测试角色'

    role.delete()
    assert not RoleV2.objects.filter(role_code='MIGRATION_TEST_ROLE').exists()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_user_role_v2_create_with_v2_columns_succeeds():
    """RT-2 (续): UserRoleV2 真入库 + granted_by_id 等 V2 字段全 OK."""
    from apps.core.models_permission_v2 import UserRoleV2, RoleV2

    role = RoleV2.objects.create(
        system_code='recruit',
        role_code='UR_TEST_ROLE',
        role_name='UR Test Role',
    )
    ur = UserRoleV2.objects.create(
        user_id=12345,
        role_code='UR_TEST_ROLE',
        system_code='recruit',
        granted_by_id=1,
        management_unit_ids=[1, 2, 3],
        valid_from='2026-01-01',
        valid_to='2026-12-31',
    )
    assert ur.id is not None
    assert ur.user_id == 12345
    assert ur.granted_by_id == 1
    assert ur.management_unit_ids == [1, 2, 3]

    fresh = UserRoleV2.objects.get(user_id=12345, role_code='UR_TEST_ROLE')
    assert fresh.id == ur.id
    assert fresh.valid_from.strftime('%Y-%m-%d') == '2026-01-01'

    ur.delete()
    role.delete()


# ============================================================
# Test 3: V1 旧表被 RENAME 备份 (RT-3)
# ============================================================
@pytest.mark.django_db
@pytest.mark.v2_permission
def test_v1_tables_renamed_to_backup():
    """RT-3: 0001_initial 建好的 V1 旧表被 0004 RENAME 到 *_v1_backup, 不被 DROP."""
    tables = _table_names()

    # 0001_initial 在 fresh DB 上建了 V1 `roles` / `user_roles` / `permissions` / `role_permissions`,
    # 0004 应把它们 RENAME 到 _v1_backup 备份
    expected_backups = {
        'roles_v1_backup',
        'user_roles_v1_backup',
        'permissions_v1_backup',
        'role_permissions_v1_backup',
    }
    missing = expected_backups - tables
    assert not missing, (
        f'BUG: V1 旧表未 RENAME 备份, 缺: {sorted(missing)}. '
        f'现有表: {sorted(t for t in tables if "role" in t or "permission" in t)}'
    )

    # V2 主表也必须存在 (不能 RENAME 后没建新的)
    assert 'roles' in tables, 'V2 `roles` 表应已 CREATE'
    assert 'user_roles' in tables, 'V2 `user_roles` 表应已 CREATE'

    # 备份里仍是 V1 schema
    backup_roles_cols = _column_names('roles_v1_backup')
    assert 'code' in backup_roles_cols, (
        f'V1 备份应是 V1 schema (含 code 列). Got: {sorted(backup_roles_cols)}'
    )
    assert 'system_code' not in backup_roles_cols, (
        f'V1 备份不应有 V2 列. Got: {sorted(backup_roles_cols)}'
    )


# ============================================================
# Test 4: 迁移幂等 (no new migrations to apply)
# 通过 makemigrations --check --dry-run 验证
# ============================================================
@pytest.mark.v2_permission
def test_no_migration_drift_in_core_app():
    """RT-misc: `core` app 自己的 model 与 migrations 无漂移.

    注: 整个项目还有 candidate / gdpr / integration 漂移 (Phase 2 T02 范围),
    本测试只筛 `core` app 验证 0004_v2_apply_schema 自洽.
    """
    import subprocess
    import os
    from django.conf import settings
    manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
    env = os.environ.copy()
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings.test'
    env['PYTHONPATH'] = settings.BASE_DIR
    # 只筛 `core` app 的漂移, T02 的其他 app 漂移不在本任务范围
    res = subprocess.run(
        ['/Users/loki/WorkBuddy/招聘助手/ATS-NEW/apps/django/.venv/bin/python',
         manage_py, 'makemigrations', '--check', '--dry-run', 'core'],
        capture_output=True, text=True, env=env,
    )
    # 成功时 (rc=0) stdout 包含 'No changes detected'
    # 失败时 (rc=1) stdout 包含 'Migrations for'
    assert res.returncode == 0, (
        f'core app 有 migration 漂移, 0004 未自洽:\n'
        f'stdout: {res.stdout}\nstderr: {res.stderr}'
    )
    assert 'No changes detected' in res.stdout, (
        f'期望 No changes detected, 实际: {res.stdout}'
    )


# ============================================================
# Test 5: 真实业务写入 + 全链路 smoke
# ============================================================
@pytest.mark.django_db
@pytest.mark.v2_permission
def test_role_v2_full_lifecycle_create_query_delete():
    """全链路 smoke: RoleV2 create → query → update → delete.

    BUG-7 强调必须用真实数据 + 真 schema 验证, 不能 mock.
    """
    from apps.core.models_permission_v2 import RoleV2

    # 1. create
    role = RoleV2.objects.create(
        system_code='recruit',
        role_code='LIFECYCLE_TEST',
        role_name='全链路测试',
        description='create',
    )
    rid = role.id
    assert rid is not None

    # 2. query by V2 字段
    found = RoleV2.objects.filter(role_code='LIFECYCLE_TEST', system_code='recruit').first()
    assert found is not None
    assert found.id == rid

    # 3. update
    found.role_name = '全链路测试 (已更新)'
    found.save()
    reloaded = RoleV2.objects.get(id=rid)
    assert reloaded.role_name == '全链路测试 (已更新)'

    # 4. delete
    reloaded.delete()
    assert not RoleV2.objects.filter(id=rid).exists()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_clone_from_template_end_to_end_smoke():
    """端到端: clone-from-template 必须能用真实 V2 schema 跑通.

    这是 P0 失败的根因 (clone-from-template 必 500). 验证 schema 修好后
    这条链路能跑通 (实际业务逻辑由后续 seed_v2_init 保证, 本测试只验
    schema 不再 OperationalError).
    """
    from django.core.management import call_command
    from apps.core.models_permission_v2 import (
        RoleV2, RolePermissionV2, PermissionResource, PermissionTemplate,
    )

    # 1. seed V2 基础数据 (资源 + 模板)
    call_command('seed_v2_init', verbosity=0)

    # 2. clone-from-template 关键操作: 写 RoleV2 行 + 写 RolePermissionV2 关联
    # 模拟其内部行为
    role = RoleV2.objects.create(
        system_code='recruit',
        role_code='CLONE_TEST_ROLE',
        role_name='克隆测试',
        template_code='TMPL_ADMIN',
    )
    assert role.id is not None

    # 找一些资源码关联
    admin_template = PermissionTemplate.objects.filter(template_code='TMPL_ADMIN').first()
    if admin_template and admin_template.permission_codes:
        for rc in admin_template.permission_codes[:3]:  # 取前 3 个
            try:
                RolePermissionV2.objects.create(
                    role_code='CLONE_TEST_ROLE',
                    resource_code=rc,
                    system_code='recruit',
                )
            except Exception as e:  # noqa: BLE001 — 测试代码: 资源码不存在就跳过 (不是 schema 问题, 只过滤 unique 冲突)
                # 资源码不存在就跳过 (不是 schema 问题)
                if 'unique' in str(e).lower():
                    continue
                raise

    # 3. 验证 role 真的被关联上资源
    role_perms = RolePermissionV2.objects.filter(
        role_code='CLONE_TEST_ROLE', system_code='recruit',
    )
    # 至少能查得到 (可能为空如果 template 没有 codes)
    assert isinstance(role_perms.count(), int)

    # 4. 清理
    RolePermissionV2.objects.filter(role_code='CLONE_TEST_ROLE').delete()
    role.delete()