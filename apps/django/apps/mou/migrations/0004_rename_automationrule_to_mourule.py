"""Phase 4（2026-09-01）：消除 mou.AutomationRule 与 automation.AutomationRule 的命名冲突。

仅重命名 Python 模型类（AutomationRule → MouRule）；模型 Meta.db_table 显式设为
'mou_automation_rules'，Django 的 RenameModel 在 db_table 非自动生成时**不会**改动
物理表名，因此历史数据（行）完整保留，零迁移抖动（设计文档 §1.2 / §3.6）。

依赖当前叶子 0003（moucontainer 字段扩展），作为后续新迁移正确接入。
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mou', '0003_moucontainer_description_moucontainer_quota_status_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AutomationRule',
            new_name='MouRule',
        ),
    ]
