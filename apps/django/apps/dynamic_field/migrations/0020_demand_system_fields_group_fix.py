"""数据一致性修复: 确保 Demand 预置系统字段统一归属「招聘需求」模块 + 「系统信息」分组。

2026-09-27 (兵哥): 种子迁移 0019 的 else 分支(认领已存在行)仅置 is_system/group 相关字段,
未强制补 module_id; 个别存量行(如 headcount)因此 module_id/group_id 为空, 在前端被归入
「未分组」而非「系统信息」。本迁移对全部 DEMAND_SYSTEM_FIELDS 行强制回填
module_id/group_id/group_name/is_system 并复活软删, 幂等可重复执行。
"""
from django.db import migrations

from apps.dynamic_field.system_fields import (
    DEMAND_SYSTEM_FIELDS,
    SYSTEM_GROUP_CODE,
    SYSTEM_GROUP_NAME,
)


def _new_id():
    from nanoid import generate as nanoid_generate
    return nanoid_generate(size=21)


def fix_demand_system_fields(apps, schema_editor):
    DynamicField = apps.get_model('dynamic_field', 'DynamicField')
    FieldModule = apps.get_model('dynamic_field', 'FieldModule')
    FieldGroup = apps.get_model('dynamic_field', 'FieldGroup')

    module = FieldModule._base_manager.filter(resource='Demand').order_by('deleted_at').first()
    if module is None:
        module = FieldModule._base_manager.create(
            id=_new_id(), resource='Demand', code='demand', name='招聘需求',
        )
    elif module.deleted_at:
        module.deleted_at = None
        module.save(update_fields=['deleted_at'])

    group = FieldGroup._base_manager.filter(module_id=module.id, code=SYSTEM_GROUP_CODE).first()
    if group is None:
        group = FieldGroup._base_manager.create(
            id=_new_id(), module_id=module.id, code=SYSTEM_GROUP_CODE,
            name=SYSTEM_GROUP_NAME, order_index=0,
        )
    elif group.deleted_at:
        group.deleted_at = None
        group.save(update_fields=['deleted_at'])

    for spec in DEMAND_SYSTEM_FIELDS:
        row = DynamicField._base_manager.filter(
            resource='Demand', field_key=spec['field_key'],
        ).order_by('deleted_at').first()
        if row is None:
            continue  # 0019 已负责创建; 此处只修存量归属
        row.module_id = module.id
        row.group_id = group.id
        row.group_name = SYSTEM_GROUP_NAME
        row.is_system = True
        row.deleted_at = None
        row.save(update_fields=[
            'module_id', 'group_id', 'group_name', 'is_system', 'deleted_at',
        ])


def reverse_fix(apps, schema_editor):
    # 保守反向: 仅撤销 is_system 标记, 不动模块/分组归属(避免误删业务配置)
    DynamicField = apps.get_model('dynamic_field', 'DynamicField')
    DynamicField._base_manager.filter(
        resource='Demand',
        field_key__in=[s['field_key'] for s in DEMAND_SYSTEM_FIELDS],
    ).update(is_system=False)


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_field', '0019_seed_demand_system_fields'),
    ]

    operations = [
        migrations.RunPython(fix_demand_system_fields, reverse_fix),
    ]
