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

⚠️ 2026-10-14 线上修复：原无条件 migrations.RemoveConstraint('uk_user_role') /
   RemoveIndex('idx_user_id') 在「生产 MySQL」上直接报 (1091, "Can't DROP 'uk_user_role'")
   导致 migrate 卡死——生产 user_roles 实际并未以 'uk_user_role' 命名建立该唯一约束
   （0002 仅改状态不落 DDL，0004 的 CREATE 在表已存在时被跳过，库很可能由备份/手动建表
   初始化，约束名/状态与迁移链不符）。
   现改为 SafeRemove*：state_forwards 仍按原样从迁移状态移除约束/索引（保证 SQLite 重做表
   正确）；database_forwards 仅在抛 (1091 "Can't DROP" / "no such index") 时静默跳过——生产
   缺失时不再 1091；MySQL 删列时还会自动连带清除任何异号残留索引，最后 AddConstraint/
   AddIndex 以规范名重建。
"""
from django.db import migrations, models
import django.db.models.deletion
import django.db.utils


class SafeRemoveConstraint(migrations.RemoveConstraint):
    """存在才摘除的 RemoveConstraint：DB 层抛 1091 / no such index 时静默跳过。"""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        try:
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        except django.db.utils.OperationalError as exc:
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
        except django.db.utils.OperationalError as exc:
            msg = str(exc).lower()
            if 'can\'t drop' in msg or 'no such index' in msg or '1091' in msg:
                return
            raise


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_purge_orphan_permission_grants'),
    ]

    operations = [
        # 1) 摘除依赖 user_id 的约束/索引（state 仍移除，db 仅存在时删）
        SafeRemoveConstraint(
            model_name='userrolev2',
            name='uk_user_role',
        ),
        SafeRemoveIndex(
            model_name='userrolev2',
            name='idx_user_id',
        ),
        # 2) 删旧裸整型列，加同名列的 FK
        migrations.RemoveField(
            model_name='userrolev2',
            name='user_id',
        ),
        migrations.AddField(
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
        migrations.AddConstraint(
            model_name='userrolev2',
            constraint=models.UniqueConstraint(
                fields=['user', 'role_code'], name='uk_user_role',
            ),
        ),
        migrations.AddIndex(
            model_name='userrolev2',
            index=models.Index(fields=['user'], name='idx_user_id'),
        ),
    ]
