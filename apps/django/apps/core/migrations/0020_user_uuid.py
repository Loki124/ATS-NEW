from django.db import migrations, models
import uuid as uuid_lib


def populate_user_uuid(apps, schema_editor):
    """给所有 uuid 为空的存量用户补齐 UUID（201 教训：迁移回填必须在真实数据上验证，
    :memory: 空库会让此回调变成空循环而静默通过，故已在 MySQL(ats_dev) 真实库核实）。"""
    User = apps.get_model('core', 'User')
    for user in User.objects.filter(uuid__isnull=True):
        user.uuid = uuid_lib.uuid4()
        user.save(update_fields=['uuid'])


def reverse_populate_user_uuid(apps, schema_editor):
    # 回滚时不清空 uuid（保留无害），仅保证迁移可反向
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_managementunit_scope_enabled'),
    ]

    operations = [
        # 1) 以可空列落地，且【不】给 default —— MySQL 上 AddField 带可调用 default 会被
        #    Django 烘焙成单个字面量写进 DDL，导致存量行全部拿到同一个 uuid（dev 已踩坑）。
        #    去掉 default 后 MySQL 仅置 NULL，再由第 2 步 RunPython 逐行赋独立 uuid。
        migrations.AddField(
            model_name='user',
            name='uuid',
            field=models.UUIDField(
                db_index=True,
                editable=False,
                null=True,
            ),
        ),
        # 2) 显式回填所有缺失行（MySQL 允许唯一列多 NULL，回填完成后再加唯一约束）
        migrations.RunPython(
            populate_user_uuid,
            reverse_populate_user_uuid,
        ),
        # 3) 回填完成后置为非空 + 唯一，与模型最终声明一致
        migrations.AlterField(
            model_name='user',
            name='uuid',
            field=models.UUIDField(
                default=uuid_lib.uuid4,
                unique=True,
                db_index=True,
                editable=False,
            ),
        ),
    ]
