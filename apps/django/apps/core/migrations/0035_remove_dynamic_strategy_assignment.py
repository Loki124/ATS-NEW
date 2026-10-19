"""删除 DynamicStrategyAssignment(策略-角色绑定桥表).

2026-10-19 兵哥裁定: 动态策略不需要绑定角色, 策略改为全局生效
(启用中的策略对所有用户生效, 超管除外). 桥表及读写逻辑一并移除:
- views_auth.py /me 并集改为对全部启用策略取 granted_resource_codes 并集
- data_permission/enforcement.py 写范围改为过滤全部启用且管辖该模块的策略
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_dynamic_strategy_permissions'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DynamicStrategyAssignment',
        ),
    ]
