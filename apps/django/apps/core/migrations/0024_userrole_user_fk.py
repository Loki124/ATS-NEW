"""UserRoleV2.user_id: BigIntegerField → ForeignKey(User, CASCADE)（P0-3 / R3 / C5）。

为什么能直接改：User.pk 是 BigAutoField（bigint），user_id 也是 bigint，列类型不变，
只加 FK 约束（指向 core_user.id，ON DELETE CASCADE）。存量数据已在 0023 清过孤儿，
加 FK 不会失败。

迁移形态：模型侧字段名从 `user_id`(BigIntegerField) 改名为 `user`(ForeignKey)，
DB 列名保持 `user_id` 不变（FK 的 db_column='user_id'）。Django autodetector 据此生成
RemoveField('user_id') + AddField('user') —— 物理上等价于对该列做一次 ALTER：
  - 先删 `user_id` 裸整型列，再建同名列的 FK（指向 core_user.id，ON DELETE CASCADE）。

on_delete=CASCADE：删用户 → 其角色授权自动清除（PRD P0-3 验收②前半句）。

兼容性关键点：列名仍是 `user_id`，所以现有全部 `UserRoleV2.objects.filter(user_id=...)`
/ `values_list('user_id')` / 序列化器 `'user_id'` 字段 **零改动**继续工作。

⚠️ SQLite 约束坑：user_id 同时是 uk_user_role(user_id, role_code) 唯一约束 与
idx_user_id(user_id) 索引的成员。SQLite 不允许在约束/索引引用下 DROP COLUMN
（"expressions prohibited in PRIMARY KEY and UNIQUE constraints"），故本迁移先
摘约束/索引 → 删列加 FK → 用新字段名 `user` 重建同名约束/索引（物理列仍是 user_id）。
MySQL 侧等价：先 DROP INDEX/CONSTRAINT，再 MODIFY 列加 FK，再 ADD 回去。
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_purge_orphan_permission_grants'),
    ]

    operations = [
        # 1) 先摘掉依赖 user_id 的约束/索引（否则 SQLite 无法 DROP 该列）
        migrations.RemoveConstraint(
            model_name='userrolev2',
            name='uk_user_role',
        ),
        migrations.RemoveIndex(
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
