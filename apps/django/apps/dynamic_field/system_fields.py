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

2026-10-12 (兵哥) 字段结构对齐《需求字段规范》:
  - 标签对齐规范: jd→岗位职责 / requirements→任职资格 / hr→需求主责人 /
    level→需求职级 / priority→需求紧急程度 (field_key 不变, 前端 MODEL_ATTR_MAP 零改动);
  - 新增预置系统字段(补模型列, 见 demand/migrations/0006+0007):
    talent_level(人才层级) / talent_nature(职位性质) / date_range(需求起止日期) /
    sharers(需求共享人) / approval_status(审批状态);
  - 引入规范 5 分类(JD信息/基本信息/负责人信息/附件信息/其他信息), 每条 spec 带 category;
  - demand_type(需求类型) / position_title(职务) 为既有系统字段, 规范未列但按「保留已有字段」保留。
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

#: 需求类型选项 (与 demand.models.demand_type choices 对齐) — 既有字段, 规范未列但保留
_DEMAND_TYPE_OPTIONS = [
    {'value': 'SOCIAL', 'label': '社会招聘'},
    {'value': 'CAMPUS', 'label': '校园招聘'},
]

#: 优先级/紧急程度选项 (与 demand.models.priority choices 对齐)
_PRIORITY_OPTIONS = [
    {'value': 'P0', 'label': 'P0-高'},
    {'value': 'P1', 'label': 'P1-中'},
    {'value': 'P2', 'label': 'P2-低'},
]

#: 职位性质选项 (与 demand.models.talent_nature choices 对齐) — 2026-10-12 新增
_TALENT_NATURE_OPTIONS = [
    {'value': 'FULLTIME', 'label': '全职'},
    {'value': 'PARTTIME', 'label': '兼职'},
    {'value': 'INTERN', 'label': '实习'},
    {'value': 'OUTSOURCE', 'label': '外包'},
]

#: 审批状态选项 (与 demand.models.approval_status choices 对齐) — 2026-10-12 新增
_APPROVAL_STATUS_OPTIONS = [
    {'value': 'NONE', 'label': '未提交'},
    {'value': 'PENDING', 'label': '待审批'},
    {'value': 'APPROVED', 'label': '已通过'},
    {'value': 'REJECTED', 'label': '已驳回'},
]

#: 兼容旧种子(0019/0022)的「系统信息」分组; 新分类见 DEMAND_FIELD_CATEGORIES。
SYSTEM_GROUP_CODE = 'system_info'
SYSTEM_GROUP_NAME = '系统信息'

#: 规范「所属分类」→ 字段分组(code/name/order)。2026-10-12 对齐《需求字段规范》。
DEMAND_FIELD_CATEGORIES = [
    {'code': 'jd_info', 'name': 'JD信息', 'order_index': 10},
    {'code': 'basic_info', 'name': '基本信息', 'order_index': 20},
    {'code': 'owner_info', 'name': '负责人信息', 'order_index': 30},
    {'code': 'attachment_info', 'name': '附件信息', 'order_index': 40},
    {'code': 'other_info', 'name': '其他信息', 'order_index': 50},
]

#: category code → name 快速查表
_CATEGORY_NAME = {c['code']: c['name'] for c in DEMAND_FIELD_CATEGORIES}

#: Demand 预置系统字段注册表。
#: locked=True 的行锁定(仅字段类型与停用状态不可修改, 其余属性可编辑);
#: locked=False 的行可编辑(含字段类型 / 选项等结构性属性, 仅 field_key 等身份键受保护)。
#: category 为规范「所属分类」code(见 DEMAND_FIELD_CATEGORIES)。
#: 2026-10-12: jd/requirements/hr/level/priority 仅改标签(field_key 不变, 复用模型列);
#:   talent_level/talent_nature/date_range/sharers/approval_status 为新增系统字段。
DEMAND_SYSTEM_FIELDS = [
    # ===== JD信息 =====
    {
        'field_key': 'title', 'label': '需求名称', 'label_en': 'Demand Name',
        'field_type': 'TEXT', 'locked': True, 'is_required': True, 'order_index': 10,
        'category': 'jd_info',
    },
    {
        'field_key': 'jd', 'label': '岗位职责', 'label_en': 'Job Responsibilities',
        'field_type': 'MULTILINE_TEXT', 'locked': False, 'is_required': False, 'order_index': 20,
        'category': 'jd_info',
    },
    {
        'field_key': 'requirements', 'label': '任职资格', 'label_en': 'Qualifications',
        'field_type': 'MULTILINE_TEXT', 'locked': False, 'is_required': False, 'order_index': 30,
        'category': 'jd_info',
    },
    # ===== 基本信息 =====
    {
        'field_key': 'headcount', 'label': '需求人数', 'label_en': 'Headcount',
        'field_type': 'NUMBER', 'locked': False, 'is_required': True, 'order_index': 40,
        'category': 'basic_info',
    },
    {
        'field_key': 'department', 'label': '需求部门', 'label_en': 'Department',
        'field_type': 'TEXT', 'locked': False, 'is_required': True, 'order_index': 50,
        'category': 'basic_info',
    },
    {
        'field_key': 'talent_nature', 'label': '职位性质', 'label_en': 'Employment Type',
        'field_type': 'SELECT', 'options': _TALENT_NATURE_OPTIONS,
        'locked': False, 'is_required': False, 'order_index': 60,
        'category': 'basic_info',
    },
    {
        'field_key': 'level', 'label': '需求职级', 'label_en': 'Job Level',
        'field_type': 'TEXT', 'locked': False, 'is_required': False, 'order_index': 70,
        'category': 'basic_info',
    },
    {
        'field_key': 'priority', 'label': '需求紧急程度', 'label_en': 'Urgency',
        'field_type': 'SELECT', 'options': _PRIORITY_OPTIONS,
        'locked': False, 'is_required': False, 'order_index': 80,
        'category': 'basic_info',
    },
    {
        'field_key': 'talent_level', 'label': '人才层级', 'label_en': 'Talent Level',
        'field_type': 'TEXT', 'locked': False, 'is_required': False, 'order_index': 90,
        'category': 'basic_info',
    },
    {
        'field_key': 'date_range', 'label': '需求起止日期', 'label_en': 'Start / End Date',
        'field_type': 'DATE_RANGE', 'locked': False, 'is_required': False, 'order_index': 100,
        'category': 'basic_info',
    },
    # 既有系统字段(规范未列, 按「保留已有字段」保留):
    {
        'field_key': 'demand_type', 'label': '需求类型', 'label_en': 'Demand Type',
        'field_type': 'SELECT', 'options': _DEMAND_TYPE_OPTIONS,
        'locked': False, 'is_required': False, 'order_index': 110,
        'category': 'basic_info',
    },
    {
        'field_key': 'position_title', 'label': '职务', 'label_en': 'Position Title',
        'field_type': 'TEXT', 'locked': False, 'is_required': False, 'order_index': 120,
        'category': 'basic_info',
    },
    # ===== 负责人信息 =====
    {
        'field_key': 'hr', 'label': '需求主责人', 'label_en': 'HR Owner',
        'field_type': 'TEXT', 'locked': False, 'is_required': False, 'order_index': 130,
        'category': 'owner_info',
    },
    {
        'field_key': 'sharers', 'label': '需求共享人', 'label_en': 'Sharers',
        'field_type': 'MULTISELECT', 'options_source': {'type': 'internal_user'},
        'locked': False, 'is_required': False, 'order_index': 140,
        'category': 'owner_info',
    },
    # ===== 其他信息 =====
    {
        'field_key': 'code', 'label': '需求编号', 'label_en': 'Demand No.',
        'field_type': 'TEXT', 'locked': True, 'is_required': True, 'order_index': 150,
        'category': 'other_info',
    },
    {
        'field_key': 'state', 'label': '需求状态', 'label_en': 'Status',
        'field_type': 'SELECT', 'options': _DEMAND_STATE_OPTIONS,
        'locked': True, 'is_required': False, 'order_index': 160,
        'category': 'other_info',
    },
    {
        'field_key': 'approval_status', 'label': '审批状态', 'label_en': 'Approval Status',
        'field_type': 'SELECT', 'options': _APPROVAL_STATUS_OPTIONS,
        'locked': False, 'is_required': False, 'order_index': 170,
        'category': 'other_info',
    },
]

#: 规范「自定义字段」12 项 field_key (与 dynamic_field/migrations/0024 内联清单一致;
#: 该迁移已应用不可改, 此处为权威副本, test_field_structure_alignment 以
#: 「DB 实际集合 == DEMAND_SPEC_FIELD_KEYS」锁定漂移)。
_DEMAND_CUSTOM_FIELD_KEYS = (
    'external_short_name', 'position_sequence', 'work_location', 'salary_range',
    'experience_requirement', 'education_requirement', 'expected_completion_date',
    'hrbp', 'hiring_manager', 'hiring_manager_superior',
    'probation_assessment_goal', 'demand_confirmation_form',
)

#: 规范字段 key 全集(系统预置 17 + 自定义 12 = 29, 已含在系统注册表内)。
#: 数据迁移 0025 据此软删历史遗留行, 保证任何环境 resource='Demand' 的字段集合
#: 与《需求字段规范》完全一致(仅软删, 可 restore 恢复)。
DEMAND_SPEC_FIELD_KEYS = frozenset(
    [s['field_key'] for s in DEMAND_SYSTEM_FIELDS] + list(_DEMAND_CUSTOM_FIELD_KEYS)
)


def get_system_field_specs(resource: str) -> list[dict]:
    """按 resource 返回系统字段注册表(当前仅 Demand); 其他 resource 返回空。"""
    if resource == 'Demand':
        return DEMAND_SYSTEM_FIELDS
    return []


def category_name(code: str) -> str:
    """规范分类 code → 中文名(未知 code 原样返回)。"""
    return _CATEGORY_NAME.get(code, code)
