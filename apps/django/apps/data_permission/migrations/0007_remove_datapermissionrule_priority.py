"""下掉 DataPermissionRule.priority 字段（2026-10-14 P0-止血 T01）。

为什么可以安全删列：
  1. 该字段的**唯一写入点硬编码 0**（role_scope_api.upsert_modules 的两处
     ``priority=0``），enforcement 全仓从不读取它 → 删掉不改变任何裁决结果；
  2. **唯一读取点**是 DataPermissionRuleViewSet 的默认列表排序
     ``['-priority', '-created_at']``，而存量全部 priority=0 → 实际排序由
     ``-created_at`` 单独决定。改为 ``['-created_at']`` 后列表表现完全一致；
  3. 表内仅 11 行，MySQL 8.0 的 ``DROP COLUMN`` 是轻量元数据操作，无锁表风险。

不使用 SeparateDatabaseAndState：本模型从未被 SeparateDatabaseAndState 处理过
（core/migrations/0004_v2_apply_schema.py 只处理 roles / user_roles）。

本迁移只删列，不含任何数据修复；反迁移由 Django 自动生成 AddField 还原。
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('data_permission', '0006_seed_action_dictionary'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datapermissionrule',
            name='priority',
        ),
    ]