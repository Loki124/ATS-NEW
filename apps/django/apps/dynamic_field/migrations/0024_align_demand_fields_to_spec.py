"""字段结构对齐《需求字段规范》(2026-10-12 兵哥)。

目标: resource='Demand' 的 DynamicField 集合与规范字段完全一致。
规则(用户确认):
  - 复用模型列仅改标签: jd→岗位职责 / requirements→任职资格 / hr→需求主责人 /
    level→需求职级 / priority→需求紧急程度 (field_key 不变);
  - 新增预置系统字段(补模型列 demand/migrations/0006+0007): talent_level / talent_nature /
    date_range / sharers / approval_status;
  - 保留既有系统字段 demand_type(需求类型) / position_title(职务)(规范未列, 按「保留已有字段」);
  - 补 12 个自定义字段(is_system=False, 值存 DynamicFieldValue);
  - 建规范 5 分类分组(JD信息/基本信息/负责人信息/附件信息/其他信息)并归类全部字段。

做法: 按 system_fields.DEMAND_SYSTEM_FIELDS 注册表 + 本文件 _DEMAND_CUSTOM_FIELDS
逐条 get_or_create 含软删行 → 复活 + 更新标签/类型/选项/分组/排序, 幂等可重复执行。
纯 ORM, 无 MySQL 专有 SQL, SQLite 测试安全。

反向: 结构对齐涉及改标签/分组, 无法干净还原 → noop(数据对齐迁移, 不做逆操作)。
"""
from django.db import migrations
from nanoid import generate as nanoid_generate

from apps.dynamic_field.system_fields import (
    DEMAND_FIELD_CATEGORIES,
    DEMAND_SYSTEM_FIELDS,
)

#: 学历要求选项(自定义字段, 常见值)
_EDU_OPTIONS = [
    {'value': 'UNLIMITED', 'label': '不限'},
    {'value': 'COLLEGE', 'label': '大专'},
    {'value': 'BACHELOR', 'label': '本科'},
    {'value': 'MASTER', 'label': '硕士'},
    {'value': 'PHD', 'label': '博士'},
]

#: 规范「自定义字段」12 项 (is_system=False, 值存 DynamicFieldValue)。
#: 人员类(HRBP/用人经理/用人经理上级)用 PERSON + options_source=internal_user;
#: 薪资范围 RANGE_NUMBER; 期望完成日期 DATE; 需求确认表 ATTACHMENT; 试用期考核目标 MULTILINE_TEXT.
_DEMAND_CUSTOM_FIELDS = [
    # ===== JD信息 =====
    {'field_key': 'external_short_name', 'label': '对外简称', 'label_en': 'External Short Name',
     'field_type': 'TEXT', 'category': 'jd_info', 'order_index': 15},
    # ===== 基本信息 =====
    {'field_key': 'position_sequence', 'label': '岗位序列', 'label_en': 'Position Sequence',
     'field_type': 'TEXT', 'category': 'basic_info', 'order_index': 125},
    {'field_key': 'work_location', 'label': '工作地点', 'label_en': 'Work Location',
     'field_type': 'TEXT', 'category': 'basic_info', 'order_index': 126},
    {'field_key': 'salary_range', 'label': '薪资范围', 'label_en': 'Salary Range',
     'field_type': 'RANGE_NUMBER', 'category': 'basic_info', 'order_index': 127},
    {'field_key': 'experience_requirement', 'label': '经验要求', 'label_en': 'Experience',
     'field_type': 'TEXT', 'category': 'basic_info', 'order_index': 128},
    {'field_key': 'education_requirement', 'label': '学历要求', 'label_en': 'Education',
     'field_type': 'SELECT', 'options': _EDU_OPTIONS, 'category': 'basic_info', 'order_index': 129},
    {'field_key': 'expected_completion_date', 'label': '期望完成日期', 'label_en': 'Expected Completion',
     'field_type': 'DATE', 'category': 'basic_info', 'order_index': 130},
    # ===== 负责人信息 =====
    {'field_key': 'hrbp', 'label': 'HRBP', 'label_en': 'HRBP',
     'field_type': 'PERSON', 'options_source': {'type': 'internal_user'}, 'category': 'owner_info', 'order_index': 145},
    {'field_key': 'hiring_manager', 'label': '用人经理', 'label_en': 'Hiring Manager',
     'field_type': 'PERSON', 'options_source': {'type': 'internal_user'}, 'category': 'owner_info', 'order_index': 146},
    {'field_key': 'hiring_manager_superior', 'label': '用人经理上级', 'label_en': "Hiring Manager's Superior",
     'field_type': 'PERSON', 'options_source': {'type': 'internal_user'}, 'category': 'owner_info', 'order_index': 147},
    # ===== 附件信息 =====
    {'field_key': 'probation_assessment_goal', 'label': '试用期考核目标', 'label_en': 'Probation Goals',
     'field_type': 'MULTILINE_TEXT', 'category': 'attachment_info', 'order_index': 10},
    {'field_key': 'demand_confirmation_form', 'label': '需求确认表', 'label_en': 'Demand Confirmation',
     'field_type': 'ATTACHMENT', 'category': 'attachment_info', 'order_index': 20},
]


def _new_id() -> str:
    """迁移历史模型不带真实模型 save() 重载(nanoid 主键), 须显式生成 id。"""
    return nanoid_generate(size=21)


def _upsert(DynamicField, module, group, spec, is_system):
    """按 (resource='Demand', field_key) get_or_create 含软删行 → 复活 + 对齐属性。"""
    row = DynamicField._base_manager.filter(
        resource='Demand', field_key=spec['field_key'],
    ).order_by('deleted_at').first()

    attrs = {
        'label': spec['label'],
        'label_en': spec.get('label_en', ''),
        'field_type': spec['field_type'],
        'is_system': is_system,
        'is_visible': True,
        'order_index': spec.get('order_index', 0),
        'group_name': group.name,
        'module_id': module.id,
        'group_id': group.id,
        'deleted_at': None,
    }
    if 'options' in spec:
        attrs['options'] = spec['options']
    if 'options_source' in spec:
        attrs['options_source'] = spec['options_source']
    if 'is_required' in spec:
        attrs['is_required'] = spec['is_required']

    if row is None:
        DynamicField._base_manager.create(
            id=_new_id(), resource='Demand', field_key=spec['field_key'], **attrs,
        )
    else:
        for k, v in attrs.items():
            setattr(row, k, v)
        row.save(update_fields=list(attrs.keys()))


def align_demand_fields(apps, schema_editor):
    DynamicField = apps.get_model('dynamic_field', 'DynamicField')
    FieldModule = apps.get_model('dynamic_field', 'FieldModule')
    FieldGroup = apps.get_model('dynamic_field', 'FieldGroup')

    # 1. Demand 模块: 复用现存行(含软删复活), 否则创建
    module = FieldModule._base_manager.filter(resource='Demand').order_by('deleted_at').first()
    if module is None:
        module = FieldModule._base_manager.create(
            id=_new_id(), resource='Demand', code='demand', name='招聘需求',
        )
    elif module.deleted_at:
        module.deleted_at = None
        module.save(update_fields=['deleted_at'])

    # 2. 规范 5 分类分组 (get_or_create + 对齐名称/排序)
    groups = {}
    for cat in DEMAND_FIELD_CATEGORIES:
        g = FieldGroup._base_manager.filter(module_id=module.id, code=cat['code']).first()
        if g is None:
            g = FieldGroup._base_manager.create(
                id=_new_id(), module_id=module.id, code=cat['code'],
                name=cat['name'], order_index=cat['order_index'],
            )
        else:
            g.name = cat['name']
            g.order_index = cat['order_index']
            g.deleted_at = None
            g.save(update_fields=['name', 'order_index', 'deleted_at'])
        groups[cat['code']] = g

    # 3. 系统字段(预置): 改标签/归类 + 新增 talent_level/talent_nature/date_range/sharers/approval_status
    for spec in DEMAND_SYSTEM_FIELDS:
        _upsert(DynamicField, module, groups[spec['category']], spec, is_system=True)

    # 4. 自定义字段 12 项
    for spec in _DEMAND_CUSTOM_FIELDS:
        _upsert(DynamicField, module, groups[spec['category']], spec, is_system=False)


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_field', '0023_normalize_candidate_fields'),
    ]

    operations = [
        # 数据对齐含改标签/分组, 无法干净逆操作 → noop
        migrations.RunPython(align_demand_fields, migrations.RunPython.noop),
    ]