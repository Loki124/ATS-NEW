"""清理 Tier 1/2 之前由同步桥镜像写入的 DataPermissionRule ROW 规则.

原 UserAppDataScope 同步桥 (views_permission_v2._sync_user_data_rule / _rebuild_user_rules)
会把用户的管理单元范围镜像成 id='uads_user_<user_id>' 的 DataPermissionRule(ROW) 行,
供 enforcement.row_filter_q 消费.

Tier 3 之后行级范围改由 scope_resolver 直接计算 (scope_filter_q), 不再读写该镜像.
本迁移幂等删除所有 uads_user_* 孤儿行; 反向操作为 no-op (数据已无意义).
"""
from django.db import migrations


def _cleanup_uads_user_rules(apps, schema_editor):
    # 延迟导入避免 import-time 耦合 (core 可能尚未完全加载 / 多 app 顺序问题)
    from apps.data_permission.models import DataPermissionRule
    DataPermissionRule.objects.filter(id__startswith='uads_user_').delete()


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_merge_user_app_data_scope_into_user_role'),
        # 确保 data_permission_rules 表已存在 (apps.core 在 INSTALLED_APPS 中先于
        # data_permission, 若不显式声明依赖, 本迁移会在该表创建前执行而报
        # "no such table: data_permission_rules". data_permission.0001_initial 无依赖, 不会成环.
        ('data_permission', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(_cleanup_uads_user_rules, _noop),
    ]
