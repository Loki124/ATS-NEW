"""系统内置字段注册表 — 需求(Demand)预置字段纳入「需求字段管理」。

2026-09-27 (兵哥): 招聘系统对需求预置的「系统信息」字段(Demand 模型列, 非动态扩展)
此前硬编码在详情页, 字段管理页看不见、调不了。现统一落地为 ``resource='Demand'``
的 DynamicField 行(种子迁移 get_or_create, ``is_system=True``), 管理页可见:

  - 三个核心标识字段锁定(LOCKED): 需求编号 / 需求名称 / 需求状态 —
    仅字段类型与停用状态不可修改, 其余属性(label/英文名称/提示/必填/可见/选项/分组/排序/可见权限)均可编辑;
  - 其余系统字段(非锁定)支持修改编辑, 含字段类型 / 选项等结构性属性;
    仅核心标识 key(field_key / is_system / resource)由后端权威守卫保留,
    防止破坏系统引用(MODEL_ATTR_MAP / 联动规则)或重分类;
  - 任何系统字段均不可删除(destroy → 400)。

前端双重防护: 管理页对 isLocked 行禁用全部操作、对可编辑系统行隐藏删除、
编辑弹窗禁用字段类型; 后端守卫(views.py)为权威, 防绕过。
"""

#: 锁定的核心标识字段(仅字段类型与停用状态不可修改, 其余属性可编辑)
SYSTEM_FIELD_LOCKED_KEYS = frozenset({'code', 'title', 'state'})

#: 非锁定系统字段编辑时, 后端强制保留的核心身份 key。
#: 仅 field_key / is_system / resource 三类身份键受保护 ——
#: 改 field_key 会破坏 MODEL_ATTR_MAP / 联动规则的引用, 改 is_system/resource 会重分类;
#: 字段类型 / 选项 / 选项来源 / 子字段等结构性属性放行, 允许业务自定义(用户要求其余系统字段支持修改编辑)。
SYSTEM_FIELD_IDENTITY_KEYS = frozenset({'field_key', 'is_system', 'resource'})

#: 需求状态选项 (与 demand.models.DemandState 对齐)
_DEMAND_STATE_OPTIONS = [
    {'value': 'DRAFT', 'label': '草稿'},
    {'value': 'PENDING', 'label': '待审批'},
    {'value': 'REJECTED', 'label': '已驳回'},
    {'value': 'APPROVED', 'label': '已通过'},
    {'value': 'RECRUITING', 'label': '招聘中'},
    {'value': 'PAUSED', 'label': '已暂停'},
    {'value': 'COMPLETED', 'label': '已完成'},
    {'value': 'CANCELLED', 'label': '已取消'},
]

#: 需求类型选项 (与 demand.models.demand_type choices 对齐)
_DEMAND_TYPE_OPTIONS = [
    {'value': 'SOCIAL', 'label': '社会招聘'},
    {'value': 'CAMPUS', 'label': '校园招聘'},
]

#: 优先级选项 (与 demand.models.priority choices 对齐)
_PRIORITY_OPTIONS = [
    {'value': 'P0', 'label': 'P0-高'},
    {'value': 'P1', 'label': 'P1-中'},
    {'value': 'P2', 'label': 'P2-低'},
]

#: 系统信息分组(挂 Demand 模块下的 FieldGroup)
SYSTEM_GROUP_CODE = 'system_info'
SYSTEM_GROUP_NAME = '系统信息'

#: Demand 预置系统字段注册表。
#: locked=True 的行锁定(仅字段类型与停用状态不可修改, 其余属性可编辑);
#: locked=False 的行可编辑(含字段类型 / 选项等结构性属性, 仅 field_key 等身份键受保护)。
#: 说明: 需求描述(jd)/任职要求(requirements)走详情页固定「描述信息」区块(多行版式),
#: 不纳入本注册表, 避免与固定区块重复渲染。
DEMAND_SYSTEM_FIELDS = [
    {
        'field_key': 'code', 'label': '需求编号', 'label_en': 'Demand No.',
        'field_type': 'TEXT', 'locked': True, 'is_required': True, 'order_index': 10,
    },
    {
        'field_key': 'title', 'label': '需求名称', 'label_en': 'Demand Name',
        'field_type': 'TEXT', 'locked': True, 'is_required': True, 'order_index': 20,
    },
    {
        'field_key': 'state', 'label': '需求状态', 'label_en': 'Status',
        'field_type': 'SELECT', 'options': _DEMAND_STATE_OPTIONS,
        'locked': True, 'is_required': False, 'order_index': 30,
    },
    {
        'field_key': 'demand_type', 'label': '需求类型', 'label_en': 'Demand Type',
        'field_type': 'SELECT', 'options': _DEMAND_TYPE_OPTIONS,
        'locked': False, 'is_required': False, 'order_index': 40,
    },
    {
        'field_key': 'department', 'label': '需求部门', 'label_en': 'Department',
        'field_type': 'TEXT', 'locked': False, 'is_required': True, 'order_index': 50,
    },
    {
        'field_key': 'headcount', 'label': '需求人数', 'label_en': 'Headcount',
        'field_type': 'NUMBER', 'locked': False, 'is_required': True, 'order_index': 60,
    },
    {
        'field_key': 'priority', 'label': '优先级', 'label_en': 'Priority',
        'field_type': 'SELECT', 'options': _PRIORITY_OPTIONS,
        'locked': False, 'is_required': False, 'order_index': 70,
    },
    {
        'field_key': 'level', 'label': '职级', 'label_en': 'Job Level',
        'field_type': 'TEXT', 'locked': False, 'is_required': False, 'order_index': 80,
    },
    {
        'field_key': 'position_title', 'label': '职务', 'label_en': 'Position Title',
        'field_type': 'TEXT', 'locked': False, 'is_required': False, 'order_index': 90,
    },
    {
        'field_key': 'hr', 'label': '负责HR', 'label_en': 'HR Owner',
        'field_type': 'TEXT', 'locked': False, 'is_required': False, 'order_index': 100,
    },
]


def get_system_field_specs(resource: str) -> list[dict]:
    """按 resource 返回系统字段注册表(当前仅 Demand); 其他 resource 返回空。"""
    if resource == 'Demand':
        return DEMAND_SYSTEM_FIELDS
    return []
