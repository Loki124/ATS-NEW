"""PermissionResource 新增「受策略管控」布尔字段 strategy_governed (2026-10-20)。

用途：动态策略「受限功能」候选区的开关 —— 只有本字段为 True 的 BUTTON 资源
才会经 `GET /api/v1/dynamic-strategies/options/` 的 governedResources 下发，
供管理员勾选后写入 DynamicStrategy.granted_resource_codes。

设计取舍：
- 独立 BooleanField 而非复用既有的 ext_fields(JSON)：布尔可索引、有 schema
  约束、可直接进序列化器与 ORM 过滤；ext_fields 自 0002 建表以来零业务使用，
  且未进序列化器, 用它等于造第二个不可校验的暗字段。
- 缺省 False：未登记的资源不进入策略管辖面，「不配置 = 不受限」是安全默认，
  避免新增资源被策略静默接管。
- 置位不进 seed_v2_init.RESOURCES：seed 对四元组无条件 update_or_create,
  且 test_resource_code_convention 多处按 4 元解包, 改元组结构会连带破坏护栏。
  置位由 0040 数据迁移承担(幂等 + 双向可逆)。

本迁移仅 AddField（MySQL 加带默认值的布尔列不重写表数据，存量行一律 False）。
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_rename_user_role_resources_to_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='permissionresource',
            name='strategy_governed',
            field=models.BooleanField(default=False, verbose_name='受策略管控'),
        ),
    ]
