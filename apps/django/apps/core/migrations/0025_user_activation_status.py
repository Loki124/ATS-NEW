"""core.User 新增 activation_status 三态字段（待激活 / 已激活 / 已停用）。

2026-10-18 兵哥：用户管理引入三态账号状态，真相源为 activation_status，
Django 内置 is_active 由 User.set_activation_status() 同步维护（兼容
ModelBackend.user_can_authenticate 与既有 is_active 过滤/索引）。

存量回填策略：
- AddField 用**字符串字面量** default='ACTIVE'（⚠️ 绝不能用可调用 default：
  MySQL 上 Django 会把可调用 default 烘焙成单个字面量写进 DDL，见 0020 uuid 教训）。
- 随后 RunPython：凡 is_active=False 的存量行 → 'DISABLED'（覆盖软删停用/管理员停用）。
- 其余（is_active=True）保持用 AddField 落下的 'ACTIVE'。

可反向：ReverseAlter 时直接删列（三态是新增信息，回滚即丢失，不再回填 is_active，
因为 is_active 从未被本迁移改动过）。
"""
from django.db import migrations, models


def backfill_activation_status(apps, schema_editor):
    """存量 is_active=False 的行 → DISABLED；其余保持 AddField 的 ACTIVE。

    用 .update() 批量而非逐行 save()：本迁移不回填 is_active（本来就对），
    只补新列，故无需触发 updated_at 自动更新。
    """
    User = apps.get_model('core', 'User')
    User.objects.filter(is_active=False).update(activation_status='DISABLED')
    User.objects.filter(is_active=True).update(activation_status='ACTIVE')


def reverse_backfill(apps, schema_editor):
    # 回滚时新列即将被删，无需恢复任何东西
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_userrole_user_fk'),
    ]

    operations = [
        # 1) 字符串字面量 default（非可调用），存量行先统一拿 'ACTIVE'
        migrations.AddField(
            model_name='user',
            name='activation_status',
            field=models.CharField(
                choices=[('PENDING', '待激活'), ('ACTIVE', '已激活'), ('DISABLED', '已停用')],
                default='ACTIVE',
                db_index=True,
                max_length=16,
                verbose_name='激活状态',
            ),
        ),
        # 2) 按 is_active 修正存量：停用账号落 DISABLED
        migrations.RunPython(backfill_activation_status, reverse_backfill),
    ]
