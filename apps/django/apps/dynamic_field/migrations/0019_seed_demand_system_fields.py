"""种子: 需求(Demand)预置系统字段落成 resource='Demand' 的 DynamicField 行。

2026-09-27 (兵哥): 招聘系统对需求预置的「系统信息」字段纳入需求字段管理。
按 apps/dynamic_field/system_fields.py 注册表 get_or_create:

  - 不存在 → 创建(is_system=True, 挂「系统信息」分组);
  - 已存在(含软删) → 认领: 复活软删行 + 置 is_system=True + 挂「系统信息」分组,
    其余属性(用户已配置的 label/类型等)保持不动;
  - 幂等: 重复执行无副作用。

纯 ORM 操作, 无 MySQL 专有 SQL, SQLite 测试安全。
"""
from django.db import migrations
from nanoid import generate as nanoid_generate

from apps.dynamic_field.system_fields import (
    DEMAND_SYSTEM_FIELDS,
    SYSTEM_GROUP_CODE,
    SYSTEM_GROUP_NAME,
)


def _new_id() -> str:
    """迁移历史模型不带真实模型 save() 重载(nanoid 主键), 须显式生成 id。"""
    return nanoid_generate(size=21)


def seed_demand_system_fields(apps, schema_editor):
    DynamicField = apps.get_model('dynamic_field', 'DynamicField')
    FieldModule = apps.get_model('dynamic_field', 'FieldModule')
    FieldGroup = apps.get_model('dynamic_field', 'FieldGroup')

    # 1. Demand 模块: 优先复用现存行(含软删复活), 否则创建
    module = FieldModule._base_manager.filter(resource='Demand').order_by('deleted_at').first()
    if module is None:
        module = FieldModule._base_manager.create(
            id=_new_id(), resource='Demand', code='demand', name='招聘需求',
        )
    elif module.deleted_at:
        module.deleted_at = None
        module.save(update_fields=['deleted_at'])

    # 2. 「系统信息」分组: unique_together (module, code) 含软删占位, 须 _base_manager 查重
    group = FieldGroup._base_manager.filter(module_id=module.id, code=SYSTEM_GROUP_CODE).first()
    if group is None:
        group = FieldGroup._base_manager.create(
            id=_new_id(), module_id=module.id, code=SYSTEM_GROUP_CODE,
            name=SYSTEM_GROUP_NAME, order_index=0,
        )
    elif group.deleted_at:
        group.deleted_at = None
        group.save(update_fields=['deleted_at'])

    # 3. 逐个 get_or_create / 认领
    for spec in DEMAND_SYSTEM_FIELDS:
        row = DynamicField._base_manager.filter(
            resource='Demand', field_key=spec['field_key'],
        ).order_by('deleted_at').first()
        if row is None:
            DynamicField._base_manager.create(
                id=_new_id(),
                resource='Demand',
                field_key=spec['field_key'],
                label=spec['label'],
                label_en=spec.get('label_en', ''),
                field_type=spec['field_type'],
                options=spec.get('options', []),
                is_required=spec.get('is_required', False),
                is_visible=True,
                order_index=spec.get('order_index', 0),
                group_name=SYSTEM_GROUP_NAME,
                module_id=module.id,
                group_id=group.id,
                is_system=True,
            )
        else:
            row.is_system = True
            row.deleted_at = None
            row.group_id = group.id
            row.group_name = SYSTEM_GROUP_NAME
            row.save(update_fields=['is_system', 'deleted_at', 'group_id', 'group_name'])


def unseed_demand_system_fields(apps, schema_editor):
    """反向: 仅撤销 is_system 标记(不删行, 保持幂等可逆的保守语义)。"""
    DynamicField = apps.get_model('dynamic_field', 'DynamicField')
    DynamicField._base_manager.filter(
        resource='Demand',
        field_key__in=[s['field_key'] for s in DEMAND_SYSTEM_FIELDS],
    ).update(is_system=False)


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_field', '0018_dynamicfield_is_system'),
    ]

    operations = [
        migrations.RunPython(seed_demand_system_fields, unseed_demand_system_fields),
    ]
