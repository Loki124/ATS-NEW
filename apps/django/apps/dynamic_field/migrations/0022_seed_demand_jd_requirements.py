"""种子: 需求描述(jd)/候选人要求(requirements) 纳入 Demand 系统字段注册表。

2026-09-28 (兵哥): 用户要求需求详情/编辑与「表单设置」完全一致 —
原 jd/requirements 走详情页固定「描述信息」区块(配置外渲染), 现纳入
resource='Demand' 的 DynamicField 行(挂「系统信息」分组), 可在
需求字段管理/表单设置中配置显隐/必填/分组。值仍存 Demand 模型列
(前端 MODEL_ATTR_MAP 映射), 不写 DynamicFieldValue。

按 0019 模式 get_or_create, 幂等可重复执行; 纯 ORM, 无 MySQL 专有 SQL。
"""
from django.db import migrations
from nanoid import generate as nanoid_generate

from apps.dynamic_field.system_fields import (
    SYSTEM_GROUP_CODE,
    SYSTEM_GROUP_NAME,
)

#: 本迁移仅负责的新增字段 key(不触碰 0019 已种的其他系统字段)
_NEW_FIELD_SPECS = [
    {'field_key': 'jd', 'label': '需求描述', 'label_en': 'Description',
     'field_type': 'MULTILINE_TEXT', 'is_required': False, 'order_index': 110},
    {'field_key': 'requirements', 'label': '候选人要求', 'label_en': 'Requirements',
     'field_type': 'MULTILINE_TEXT', 'is_required': False, 'order_index': 120},
]


def _new_id() -> str:
    """迁移历史模型不带真实模型 save() 重载(nanoid 主键), 须显式生成 id。"""
    return nanoid_generate(size=21)


def seed_jd_requirements(apps, schema_editor):
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

    for spec in _NEW_FIELD_SPECS:
        row = DynamicField._base_manager.filter(
            resource='Demand', field_key=spec['field_key'],
        ).order_by('deleted_at').first()
        if row is None:
            DynamicField._base_manager.create(
                id=_new_id(),
                resource='Demand',
                field_key=spec['field_key'],
                label=spec['label'],
                label_en=spec['label_en'],
                field_type=spec['field_type'],
                is_required=spec['is_required'],
                is_visible=True,
                order_index=spec['order_index'],
                group_name=SYSTEM_GROUP_NAME,
                module_id=module.id,
                group_id=group.id,
                is_system=True,
            )
        else:
            # 已存在(含软删): 复活 + 认领, 用户已配置的属性保持不动
            row.is_system = True
            row.deleted_at = None
            row.module_id = module.id
            row.group_id = group.id
            row.group_name = SYSTEM_GROUP_NAME
            row.save(update_fields=[
                'is_system', 'deleted_at', 'module_id', 'group_id', 'group_name',
            ])


def unseed_jd_requirements(apps, schema_editor):
    """反向: 仅撤销 is_system 标记(不删行, 保守幂等)。"""
    DynamicField = apps.get_model('dynamic_field', 'DynamicField')
    DynamicField._base_manager.filter(
        resource='Demand', field_key__in=[s['field_key'] for s in _NEW_FIELD_SPECS],
    ).update(is_system=False)


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_field', '0021_alter_dynamicfield_field_type'),
    ]

    operations = [
        migrations.RunPython(seed_jd_requirements, unseed_jd_requirements),
    ]
