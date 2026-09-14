"""T01.2: 删除 V1 Permission 模型, 单一真相源收敛到 V2 PermissionResource.

背景:
- 0001_initial 曾建 `permissions` 表并定义 V1 Permission 模型.
- 0004_v2_apply_schema 将物理 `permissions` 表 RENAME 为 `permissions_v1_backup`
  (保留救援路径), 但 Django state 里 Permission 模型一直保留 (当时 init_demo_data.py
  还 import 它).
- 2026-09-11 init_demo_data.py 死文件已删, Permission 再无活引用, 可安全删除.

设计:
- 物理删除用幂等 DROP TABLE IF EXISTS (0004 已 rename, 多数环境此表已不存在, IF EXISTS 保证无害).
- state 删除用 DeleteModel, 仅从 Django 迁移图移除模型, 不再发 DDL.
- 用 SeparateDatabaseAndState 分离两者, 避免 DeleteModel 默认 DROP TABLE 对已 rename 表报错.

依赖: 串在 0006_department_multi_roles 之后, 避免与 core app 已有叶子节点冲突.
"""

from django.db import migrations


def _drop_permission_table(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        # 幂等: 0004 已将物理表 rename 为 permissions_v1_backup, 此处通常已不存在
        cursor.execute(
            "DROP TABLE IF EXISTS {tbl}".format(
                tbl=schema_editor.quote_name('permissions')
            )
        )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0006_department_multi_roles'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_drop_permission_table, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.DeleteModel(name='Permission'),
            ],
        ),
    ]
