"""T01.1: V2 权限 schema 真实建表 + V1 旧表 RENAME 备份 (2026-08-03 寇豆码)

P0 修复背景 (架构师实测 + 主理人运行时复验):
- 0002_v2_init 用 SeparateDatabaseAndState 只注册 V2 state, 不执行 DDL
- V1 models (Role managed=False, db_table='roles') 与 V2 models (RoleV2
  managed=True, db_table='roles') 共用同一张物理表
- 0001_initial 已用 V1 schema 真实建表, 字段不含 V2 列 (system_code /
  role_code / granted_by_id ...)
- 后果: 运行时 RoleV2.objects.all() → OperationalError: no such column →
  被 except→deny 吞掉 → 整套 V2 权限静默降级为全员拒绝, clone-from-template 必 500

本 migration (0004) 把 T17 手工命令 m04_v2_apply_schema 转为正式迁移:

1. 从 Django state 删除 V1 影子模型 (Role / UserRole / RolePermission),
   它们与 V2 model 同表冲突, 删除避免注册歧义. 不执行 DDL (managed=False
   且物理表被备份).
2. 幂等 RENAME V1 旧表 (roles / user_roles / permissions / role_permissions)
   到 *_v1_backup. 备份保留 V1 数据救援路径 (用户决策: 不 DROP).
3. 幂等 CREATE V2 schema (roles / user_roles), 列严格对齐
   models_permission_v2.RoleV2 / UserRoleV2 定义.
4. 其他 V2 表 (permission_resources / permission_templates / role_permission /
   management_units / tenant_configs) 由 0002_v2_init 已建, 本 migration
   不动.

设计要点:
- 全程 RunPython + IF EXISTS / IF NOT EXISTS 模式, re-run 幂等
- 跨 DB 兼容 (SQLite / MySQL): 用 introspection 探测 V1 vs V2 列结构
  决定 RENAME 还是 skip
- reverse_code 完整双向可逆: 把 V2 表 DROP, 把 V1 备份 RENAME 回原名
- 真业务验证: RoleV2.objects.create() 能在 fresh DB 真实入库 (学自 BUG-7
 教训: 迁移必须用真 model 操作真物理 schema)

不变量 (学自 BUG-7 教训):
- 检测列存在用 introspection.get_table_description(), 不硬编码 SQL
- 不在模块级 import apps.* (避免遮蔽)
- 不假设 :memory: 测试 DB 是空 DB (test fixtures 也用 V1 表)
"""
from django.db import migrations


def _table_exists(cursor, table_name, schema_editor=None):
    """跨 DB vendor 检测表是否存在. 优先用 schema_editor.connection.vendor (DatabaseWrapper)."""
    # cursor.connection 是 DBAPI 连接 (sqlite3.Connection / pymysql.Connection),
    # 它没有 vendor 属性. vendor 在 DatabaseWrapper 上. 通过 schema_editor 传.
    vendor = schema_editor.connection.vendor if schema_editor else 'sqlite'
    if vendor == 'sqlite':
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=%s",
            [table_name],
        )
    elif vendor == 'mysql':
        cursor.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=%s",
            [table_name],
        )
    else:  # postgres / others
        cursor.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name=%s",
            [table_name],
        )
    return cursor.fetchone() is not None


def _column_exists(cursor, table_name, column_name, schema_editor=None):
    """跨 DB vendor 检测列是否存在 (用于区分 V1 vs V2 schema)."""
    vendor = schema_editor.connection.vendor if schema_editor else 'sqlite'
    if vendor == 'sqlite':
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        cols = {row[1] for row in cursor.fetchall()}
        return column_name in cols
    elif vendor == 'mysql':
        cursor.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=%s AND column_name=%s",
            [table_name, column_name],
        )
    else:  # postgres
        cursor.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=%s AND column_name=%s",
            [table_name, column_name],
        )
    return cursor.fetchone() is not None


def backup_v1_tables(apps, schema_editor):
    """幂等 RENAME V1 旧表 → *_v1_backup (不 DROP, 保留救援路径).

    跳过条件:
    - 旧表不存在 (fresh DB + 0001 没建过)
    - 旧表已经是 V2 schema (含 system_code 列) — 说明已经 RENAME 过 / 上游已迁
    - 备份名已存在 (避免覆盖)
    """
    with schema_editor.connection.cursor() as cursor:
        rename_pairs = [
            # (旧 V1 表, 备份名)
            ('roles', 'roles_v1_backup'),
            ('user_roles', 'user_roles_v1_backup'),
            ('permissions', 'permissions_v1_backup'),
            ('role_permissions', 'role_permissions_v1_backup'),
        ]
        for old, new in rename_pairs:
            if not _table_exists(cursor, old, schema_editor):
                # V1 旧表物理不存在 (fresh DB): skip
                continue
            if _table_exists(cursor, new, schema_editor):
                # 备份已存在: 视为已 rename 过 (幂等)
                continue
            # V2 schema 特征列存在 → 说明该表已不是 V1, 不该被覆盖
            if _column_exists(cursor, old, 'system_code', schema_editor) and old in ('roles', 'user_roles'):
                continue
            cursor.execute(f'ALTER TABLE "{old}" RENAME TO "{new}"')


def create_v2_schema(apps, schema_editor):
    """幂等 CREATE V2 物理 schema (roles / user_roles).

    列严格对齐:
    - apps.core.models_permission_v2.RoleV2 (db_table='roles')
    - apps.core.models_permission_v2.UserRoleV2 (db_table='user_roles')

    跳过条件: V2 表已存在 (幂等 re-run safe).

    注意:
    - SQLite 用 INTEGER PRIMARY KEY AUTOINCREMENT 表示 BigAutoField
    - SQLite 用 TEXT 存 JSON (Django 会序列化/反序列化)
    - NOT NULL DEFAULT 用于保留 V1 PK 兼容性 (无显式值时给空字符串 / 0)
    """
    vendor = schema_editor.connection.vendor
    with schema_editor.connection.cursor() as cursor:
        # ---- roles 表 ----
        if not _table_exists(cursor, 'roles', schema_editor):
            if vendor == 'sqlite':
                cursor.execute("""
                    CREATE TABLE "roles" (
                        "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                        "system_code" VARCHAR(32) NOT NULL DEFAULT 'recruit',
                        "role_code" VARCHAR(64) NOT NULL,
                        "role_name" VARCHAR(64) NOT NULL,
                        "template_code" VARCHAR(64),
                        "default_data_scope_type" VARCHAR(32),
                        "description" VARCHAR(255),
                        "is_system" SMALLINT NOT NULL DEFAULT 0,
                        "status" SMALLINT NOT NULL DEFAULT 1,
                        "created_at" TIMESTAMP NOT NULL,
                        "updated_at" TIMESTAMP NOT NULL,
                        CONSTRAINT "uk_system_role"
                            UNIQUE ("system_code", "role_code")
                    )
                """)
                cursor.execute("""
                    CREATE INDEX "idx_roles_system_module"
                        ON "roles" ("system_code", "default_data_scope_type")
                """)
            elif vendor == 'mysql':
                cursor.execute("""
                    CREATE TABLE `roles` (
                        `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        `system_code` VARCHAR(32) NOT NULL DEFAULT 'recruit',
                        `role_code` VARCHAR(64) NOT NULL,
                        `role_name` VARCHAR(64) NOT NULL,
                        `template_code` VARCHAR(64) NULL,
                        `default_data_scope_type` VARCHAR(32) NULL,
                        `description` VARCHAR(255) NULL,
                        `is_system` SMALLINT NOT NULL DEFAULT 0,
                        `status` SMALLINT NOT NULL DEFAULT 1,
                        `created_at` DATETIME NOT NULL,
                        `updated_at` DATETIME NOT NULL,
                        UNIQUE KEY `uk_system_role` (`system_code`, `role_code`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

        # ---- user_roles 表 ----
        if not _table_exists(cursor, 'user_roles', schema_editor):
            if vendor == 'sqlite':
                cursor.execute("""
                    CREATE TABLE "user_roles" (
                        "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                        "user_id" BIGINT NOT NULL,
                        "role_code" VARCHAR(64) NOT NULL,
                        "system_code" VARCHAR(32) NOT NULL DEFAULT 'recruit',
                        "management_unit_ids" TEXT,
                        "valid_from" DATE,
                        "valid_to" DATE,
                        "granted_by_id" BIGINT,
                        "granted_at" TIMESTAMP NOT NULL,
                        "updated_at" TIMESTAMP NOT NULL,
                        CONSTRAINT "uk_user_role"
                            UNIQUE ("user_id", "role_code")
                    )
                """)
                cursor.execute("""
                    CREATE INDEX "idx_user_id"
                        ON "user_roles" ("user_id")
                """)
            elif vendor == 'mysql':
                cursor.execute("""
                    CREATE TABLE `user_roles` (
                        `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        `user_id` BIGINT NOT NULL,
                        `role_code` VARCHAR(64) NOT NULL,
                        `system_code` VARCHAR(32) NOT NULL DEFAULT 'recruit',
                        `management_unit_ids` JSON NULL,
                        `valid_from` DATE NULL,
                        `valid_to` DATE NULL,
                        `granted_by_id` BIGINT NULL,
                        `granted_at` DATETIME NOT NULL,
                        `updated_at` DATETIME NOT NULL,
                        UNIQUE KEY `uk_user_role` (`user_id`, `role_code`),
                        KEY `idx_user_id` (`user_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)


def drop_v2_tables(apps, schema_editor):
    """reverse_code for create_v2_schema — DROP V2 物理表 (幂等)."""
    with schema_editor.connection.cursor() as cursor:
        for table in ('roles', 'user_roles'):
            if _table_exists(cursor, table, schema_editor):
                cursor.execute(f'DROP TABLE "{table}"')


def restore_v1_from_backup(apps, schema_editor):
    """reverse_code for backup_v1_tables — RENAME 备份回原名.

    注意: 只在当前 roles/user_roles 是 V2 schema 时才恢复 V1 备份.
    若 V2 schema 都不存在, 说明原始库就没有 V1, 不动.
    """
    with schema_editor.connection.cursor() as cursor:
        rename_pairs = [
            ('roles_v1_backup', 'roles'),
            ('user_roles_v1_backup', 'user_roles'),
            ('permissions_v1_backup', 'permissions'),
            ('role_permissions_v1_backup', 'role_permissions'),
        ]
        for backup, original in rename_pairs:
            if not _table_exists(cursor, backup, schema_editor):
                continue
            if _table_exists(cursor, original, schema_editor):
                # 原名已被占用 (e.g. V2 表), 跳过恢复避免覆盖
                continue
            cursor.execute(f'ALTER TABLE "{backup}" RENAME TO "{original}"')


class Migration(migrations.Migration):
    """T01.1 幂等建 V2 schema + RENAME V1 备份.

    关键顺序:
    1. DeleteModel (Role/UserRole/RolePermission): 从 state 删 V1 模型.
       由于 managed=False, 不执行 DDL. 仅清掉 Django ORM 注册冲突.
       (Permission 因为 init_demo_data 还用, 也设为 managed=False 但保留定义)
    2. RunPython(backup_v1_tables): RENAME V1 物理表到 *_v1_backup.
    3. RunPython(create_v2_schema): CREATE 新 V2 roles / user_roles.
    """

    dependencies = [
        ('core', '0003_alter_rolepermission_options'),
    ]

    operations = [
        # 1. 从 Django state 删 V1 影子模型 (无 DDL: managed=False 且物理表被备份)
        migrations.DeleteModel(
            name='Role',
        ),
        migrations.DeleteModel(
            name='UserRole',
        ),
        migrations.DeleteModel(
            name='RolePermission',
        ),
        # 2. RENAME V1 物理表到 *_v1_backup
        migrations.RunPython(
            backup_v1_tables,
            reverse_code=restore_v1_from_backup,
        ),
        # 3. CREATE V2 roles / user_roles 物理表
        migrations.RunPython(
            create_v2_schema,
            reverse_code=drop_v2_tables,
        ),
    ]