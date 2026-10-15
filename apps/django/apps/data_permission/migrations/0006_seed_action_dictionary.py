"""灌入动作字典种子（权限 v2，docs/plan-read-write-action-permission.md）。

把 action_map.ACTION_REGISTRY / PRESET_PACKAGES 幂等灌入 DB 字典表。
刻意 **import 业务常量** 而非自包含数据（与 metrics.0031 的自包含策略相反）：
种子的语义就是「与代码契约保持一致的完整清单」——新环境跑此迁移时应得到
当前代码的全部动作；未来 ACTION_REGISTRY 新增动作后，新环境初始化同样自动带上。
漂移防护由 test_action_map 的种子一致性用例锁定。

反向迁移 no-op：字典表清空即可（无存量数据可还原）。
"""
from django.db import migrations

from apps.data_permission import action_map


def seed_actions(apps, schema_editor):
    action_map.sync_seed(apps)


def unseed_actions(apps, schema_editor):
    DataPermissionAction = apps.get_model('data_permission', 'DataPermissionAction')
    DataPermissionActionPreset = apps.get_model('data_permission', 'DataPermissionActionPreset')
    DataPermissionAction.objects.filter(is_system=True).delete()
    DataPermissionActionPreset.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('data_permission', '0005_datapermissionaction_datapermissionactionpreset_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_actions, unseed_actions),
    ]
