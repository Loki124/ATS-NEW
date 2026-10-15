"""UserRoleV2.user_id: BigIntegerField → ForeignKey(User, CASCADE)（P0-3 / R3 / C5）。

为什么能直接改：User.pk 是 BigAutoField（bigint），user_id 也是 bigint，列类型不变，
只加 FK 约束（指向 core_user.id，ON DELETE CASCADE）。存量数据已在 0023 清过孤儿，
加 FK 不会失败。

迁移形态：模型侧字段名从 `user_id`(BigIntegerField) 改名为 `user`(ForeignKey)，
DB 列名保持 `user_id` 不变（FK 的 db_column='user_id'）。Django autodetector 据此生成
RemoveField('user_id') + AddField('user') —— 物理上等价于对该列做一次 ALTER：
  - 先摘依赖 user_id 的约束/索引 → 删列加 FK → 用新字段名 `user` 重建同名约束/索引。

on_delete=CASCADE：删用户 → 其角色授权自动清除（PRD P0-3 验收②前半句）。

兼容性关键点：列名仍是 `user_id`，所以现有全部 `UserRoleV2.objects.filter(user_id=...)`
/ `values_list('user_id')` / 序列化器 `'user_id'` 字段 **零改动**继续工作。

═══════════════════════════════════════════════════════════════════════
⚠️ 2026-10-14 线上二次修复（幂等 + 防 schema 漂移）
═══════════════════════════════════════════════════════════════════════
生产 user_roles 实际 schema 与迁移链长期漂移（0002 仅改状态不落 DDL，0004 的 CREATE
在表已存在时被跳过，库很可能由备份/手动建表初始化）。这导致两个连锁失败：

(A) (1091, "Can't DROP 'user_id'") —— 出现在「重跑」时。MySQL DDL 非事务：前一次
    失败的 0024 已经把 user_id 列 DROP 掉，但 AddField 因 (B) 失败导致迁移未落库；
    重跑时 RemoveField 再 DROP 已不存在的列 → 1091。
(B) (1826, "Duplicate foreign key constraint name 'user_roles_user_id_9d9f8dbb_fk_core_user_id'")
    —— 0004 把 V1 表 RENAME 成 user_roles_v1_backup，备份表仍保留同名 FK；0024 的
    AddField(user FK) 自动生成**同名** FK → 1826。

本版修复手段（全部异常兜底，保证可安全重跑）：
  0) `_mysql_drop_user_id_fks` RunPython（仅 MySQL 生效，SQLite no-op）先 introspect 摘除：
       · user_roles 作为子表时 user_id 上的外向 FK（阻断 DROP COLUMN）；
       · user_roles 作为父列时被其他表 FK 引用的 user_id（阻断 DROP COLUMN）；
       · 备份表 user_roles_v1_backup 占用的同名 FK 约束（释放名字，根除 1826）。
  1) SafeRemoveConstraint / SafeRemoveIndex：state 仍移除，db 层 1091/no such index 跳过。
  2) SafeRemoveField：db 层 1091/unknown column（列已不存在）跳过，兼容 (A)。
  3) SafeAddField：db 层 1060(duplicate column)/1061(duplicate key)/1826(dup FK name)/
     1091/already exists 跳过，兼容半完成态重跑。
  4) SafeAddConstraint / SafeAddIndex：db 层 1061/duplicate/already exists 跳过。

所有 Safe* 仅吞「本就不该存在 / 已存在」这一类幂等噪声，绝不吞真错误。

═══════════════════════════════════════════════════════════════════════
⚠️ 2026-10-15 线上三次修复（1452 脏数据 + 异常类型漏网）
═══════════════════════════════════════════════════════════════════════
现象：attempt 18 仍失败于 SafeAddField(L157)，报
  IntegrityError: (1452, 'Cannot add or update a child row: a foreign key
  constraint fails (... CONSTRAINT `user_roles_user_id_..._fk_core_user_id`
  FOREIGN KEY (`user_id`) REFERENCES `core_user` (`id`))')

两个独立缺陷：

(A) 异常类型漏网 —— 1452 是 **IntegrityError**，而上述所有 Safe* 只
    `except django.db.utils.OperationalError`。Django 的 wrap_database_errors
    把 pymysql 异常包成 IntegrityError(1452) / DatabaseError(1061 等)，
    完全不落在 except 分支里 → 直接冒泡 → 迁移框架无限重试卡死。
    修复：所有 Safe* 补 `except (OperationalError, IntegrityError, DatabaseError)`，
    但**仍只吞白名单里的幂等错误码**，其余一律 raise（不吞真错误）。

(B) 脏数据才是真凶 —— 0023 的 purge_orphans 只在「它自己被执行那一刻」
    删除孤儿。若孤儿数据是**之后**才进入 user_roles 的（前两次失败迁移的
    半完成态、权限管理页面又写了授权、备份恢复等），0023 早已 applied
    不会重跑，于是 AddField(user FK) 必然 1452。
    修复：在 AddField 之前**再清一次**残留孤儿（purge_residual_orphans），
    不依赖「0023 跑过」这一假设，让 0024 自洽可安全重跑。

    删除范围严格限定：仅 user_id 指向不存在用户的行（LEFT JOIN core_user
    判空），**不按 is_active 过滤**（软删用户的授权须保留）。这是不可逆
    数据删除，执行前须按 PLAN_R3 §5.5.3 备份 user_roles 三表。
"""
from django.db import migrations, models
import django.db.models.deletion
import django.db.utils

# 🔴 2026-10-15：1452 被 Django 包成 IntegrityError，只 catch OperationalError
# 会让这类错绕过 Safe* 兜底直接冒泡 → migrate 无限重试卡死（线上 attempt 18 卡死）。
# 补齐三种异常类型，但**白名单逻辑不变**：只吞幂等噪声，其余一律 raise。
_DB_EXC = (
    django.db.utils.OperationalError,
    django.db.utils.IntegrityError,
    django.db.utils.DatabaseError,
)


def _mysql_drop_user_id_fks(apps, schema_editor):
    """MySQL 专用：摘除 user_roles.user_id 上阻断 DROP COLUMN 的全部外键，
    并释放备份表占用的同名 FK 约束名，根除 1826。SQLite 直接 no-op。"""
    from django.db import connection
    if connection.vendor != 'mysql':
        return
    with connection.cursor() as cur:
        db = connection.settings_dict['NAME']

        # 1) user_roles 作为子表：user_id 列上的外向 FK（指向 core_user 等）
        cur.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'user_roles'
              AND COLUMN_NAME = 'user_id'
              AND REFERENCED_TABLE_NAME IS NOT NULL
            """,
            [db],
        )
        for (fk_name,) in cur.fetchall():
            try:
                cur.execute(f"ALTER TABLE user_roles DROP FOREIGN KEY `{fk_name}`")
            except Exception:
                pass  # 已不存在则忽略

        # 2) user_roles 作为父列：其他表对 user_roles.user_id 的 FK 引用
        cur.execute(
            """
            SELECT k.TABLE_NAME, k.CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE k
            WHERE k.TABLE_SCHEMA = %s
              AND k.REFERENCED_TABLE_NAME = 'user_roles'
              AND k.REFERENCED_COLUMN_NAME = 'user_id'
            """,
            [db],
        )
        for tbl, fk_name in cur.fetchall():
            try:
                cur.execute(f"ALTER TABLE `{tbl}` DROP FOREIGN KEY `{fk_name}`")
            except Exception:
                pass

        # 3) 备份表 user_roles_v1_backup 占用同名 FK 约束名（0004 RENAME 遗留）→ 根除 1826
        cur.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'user_roles_v1_backup'
              AND CONSTRAINT_TYPE = 'FOREIGN KEY'
            """,
            [db],
        )
        for (fk_name,) in cur.fetchall():
            try:
                cur.execute(f"ALTER TABLE user_roles_v1_backup DROP FOREIGN KEY `{fk_name}`")
            except Exception:
                pass


def purge_residual_orphans(apps, schema_editor):
    """🔴 加 FK 前最后一道清污：删除 user_roles 中 user_id 指向不存在用户的行。

    为什么 0023 清过了这里还要再清（2026-10-15 线上 1452 根因）：
      0023 只在「它被执行那一刻」删除孤儿。若孤儿数据是之后才进入
      user_roles 的（前两次失败迁移的半完成态、权限页又写了授权、备份恢复等），
      0023 早已 applied 不会重跑 → AddField(user FK) 必然 1452 失败。
      故 0024 必须自洽：不依赖「0023 跑过」这一假设，清完再加 FK。

    删除范围（严格最小化，宁可少删不可误删）：
      ✅ 只删 user_id 指向不存在用户的行（LEFT JOIN core_user 判空）
      ❌ 不按 is_active 过滤 —— 软删用户(is_active=0)的授权必须保留，
         恢复该用户后授权仍在
      ❌ 不碰 role_permission / 不碰 system_code != 'recruit' 的行

    不可逆：执行前须按 PLAN_R3 §5.5.3 备份 user_roles / role_permission /
    roles 三表（备份是本删除唯一的兜底）。
    """
    db_alias = schema_editor.connection.alias
    User = apps.get_model('core', 'User')
    UserRoleV2 = apps.get_model('core', 'UserRoleV2')

    # 🔴 2026-10-15 线上第三次翻车复盘：用 _meta.db_table + information_schema 预检查
    # 是错的 —— 该迁移的 from_state 里 UserRoleV2 尚无 `user` 字段、db_table 解析不可靠，
    # 预检查误判「列不存在」→ 直接 return 跳过清理 → 紧接着 AddField 照旧撞 1452。
    # 改为：**不做任何预检查**，直接执行删除，让「列真不存在」这一种情形由异常兜底。
    #
    # 🔴 用 ORM 子查询而非 `DELETE ur FROM ... JOIN`（MySQL 多表删除语法）：
    #    后者在 SQLite 下直接 `near "ur": syntax error`（实测），会把
    #    test settings（SQLite）的建库流程整体搞崩 → 207 errors。
    #    exclude(user_id__in=...) 是跨库通用写法，且天然「不按 is_active 过滤」。
    try:
        valid_user_ids = list(
            User.objects.using(db_alias).values_list('id', flat=True)
        )
        orphans = UserRoleV2.objects.using(db_alias).exclude(
            user_id__in=valid_user_ids
        )
        n = orphans.count()
        if n:
            detail = list(orphans.values_list('id', 'user_id', 'role_code')[:5])
            print(f'[P0-3/0024] 删除残留孤儿授权 user_roles: {n} 条，样例={detail}')
            orphans.delete()
        else:
            print('[P0-3/0024] 加 FK 前检查：无残留孤儿授权，跳过清理。')
    except django.db.utils.DatabaseError as exc:
        # 1054 Unknown column = user_id 物理列已被前次失败迁移 DROP（半完成态），
        # 此时本就无需清理，放行让后续 AddField 重建该列。
        msg = str(exc).lower()
        if '1054' in msg or 'unknown column' in msg:
            print('[P0-3/0024] user_id 物理列不存在（半完成态），跳过残留孤儿清理。')
            return
        raise


class SafeRemoveConstraint(migrations.RemoveConstraint):
    """存在才摘除的 RemoveConstraint：DB 层抛 1091 / no such index 时静默跳过。"""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        try:
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        except _DB_EXC as exc:
            msg = str(exc).lower()
            if 'can\'t drop' in msg or 'no such index' in msg or '1091' in msg:
                # 生产 MySQL 未以该名建立约束 / 已缺失：跳过（删列时 MySQL 自动连带清残留）
                return
            raise


class SafeRemoveIndex(migrations.RemoveIndex):
    """存在才摘除的 RemoveIndex：DB 层抛 1091 / no such index 时静默跳过。"""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        try:
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        except _DB_EXC as exc:
            msg = str(exc).lower()
            if 'can\'t drop' in msg or 'no such index' in msg or '1091' in msg:
                return
            raise


class SafeRemoveField(migrations.RemoveField):
    """列缺失也安全的 RemoveField：DB 层抛 1091 / unknown column 时静默跳过（兼容重跑）。"""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        try:
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        except _DB_EXC as exc:
            msg = str(exc).lower()
            if 'can\'t drop' in msg or '1091' in msg or 'unknown column' in msg \
                    or 'check that column' in msg:
                # 前次失败已删列（MySQL 非事务 DDL 半完成态）→ 跳过
                return
            raise


class SafeAddField(migrations.AddField):
    """列/FK/索引已存在也安全的 AddField：吞幂等噪声，兼容半完成态重跑。"""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        try:
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        except django.db.utils.OperationalError as exc:
            msg = str(exc).lower()
            if any(k in msg for k in (
                '1060', 'duplicate column',
                '1061', 'duplicate key',
                '1826', 'duplicate foreign key constraint name',
                '1091', 'unknown column', 'already exists',
            )):
                # 列已存在 / FK 名已占用 / 索引已存在：幂等跳过
                return
            raise


class SafeAddConstraint(migrations.AddConstraint):
    """约束已存在也安全的 AddConstraint：吞 1061 / duplicate / already exists。"""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        try:
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        except _DB_EXC as exc:
            msg = str(exc).lower()
            if any(k in msg for k in ('1061', 'duplicate', 'already exists')):
                return
            raise


class SafeAddIndex(migrations.AddIndex):
    """索引已存在也安全的 AddIndex：吞 1061 / duplicate / already exists。"""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        try:
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        except _DB_EXC as exc:
            msg = str(exc).lower()
            if any(k in msg for k in ('1061', 'duplicate', 'already exists')):
                return
            raise


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_purge_orphan_permission_grants'),
    ]

    operations = [
        # 0) MySQL 专用：先摘除 user_roles.user_id 上的 FK 并释放备份表同名约束，根除 1091/1826
        migrations.RunPython(_mysql_drop_user_id_fks, migrations.RunPython.noop),
        # 1) 摘除依赖 user_id 的约束/索引（state 仍移除，db 仅存在时删）
        SafeRemoveConstraint(
            model_name='userrolev2',
            name='uk_user_role',
        ),
        SafeRemoveIndex(
            model_name='userrolev2',
            name='idx_user_id',
        ),
        # 2) 删旧裸整型列，加同名列的 FK（均幂等安全，兼容重跑/半完成态）
        #    ⚠️ 加 FK 前必须再清一次残留孤儿 —— 0023 只清「它执行那一刻」的孤儿，
        #    之后进入的孤儿会让 AddField 撞 1452（线上 attempt 18 卡死真因）。
        #    这一步让 0024 自洽：即使 0023 早已 applied 也能安全加 FK。
        migrations.RunPython(purge_residual_orphans, migrations.RunPython.noop),
        SafeRemoveField(
            model_name='userrolev2',
            name='user_id',
        ),
        SafeAddField(
            model_name='userrolev2',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                db_index=False,
                related_name='user_roles_v2',
                to='core.user',
                db_column='user_id',
                verbose_name='用户',
            ),
        ),
        # 3) 用新字段名 `user` 重建同名约束/索引（物理列仍是 user_id）
        SafeAddConstraint(
            model_name='userrolev2',
            constraint=models.UniqueConstraint(
                fields=['user', 'role_code'], name='uk_user_role',
            ),
        ),
        SafeAddIndex(
            model_name='userrolev2',
            index=models.Index(fields=['user'], name='idx_user_id'),
        ),
    ]
