"""数据权限：模块维度 -> ORM 字段路径映射。

每个业务模块支持的「维度」(dept/owner/creator/unit/process) 在此映射到该模块模型上的
真实字段路径（相对模型，可含 FK 跨表）。维度若无真实字段 -> None，编译器 fail-safe
视为 no-op（不放行也不报错），与 scope_resolver 既有「未支持维度 no-op」语义一致。

维度约定：
  - dept    部门：候选人取推荐人部门(referrer__department_id)，其余取自身 department_id
  - owner   负责人：候选人的推荐人(referrer_id) / 需求的 HR(hr_id) / 职位的 owner(owner_id)
  - creator 创建人：统一 created_by_id（FullAuditModel 提供）
  - unit    管理单元（M03 复合维度）：值域 = 管理单元 id。它**不是单一 ORM 路径**，
    编译时经 iter_unit_scopes 展开为「部门集合 ∪ 成员用户集合」，字段路径复用本表
    既有的 dept/creator 两项（零新增字段映射）。此处以 True 作「复合维度已注册」
    标记（supported_dimensions 依 truthy 判定）；展开逻辑唯一实现点在
    expr_compiler._compile_unit_condition，禁止在别处重建单元展开。
  - process 招聘流程：本版各模块暂无稳定外键承载，统一 None（留扩展点）

值类型：dept -> 部门 id（字符串，Department.pk CharField）；owner/creator -> 用户 id（int，User.pk）；
unit -> 管理单元 id（int，ManagementUnit.pk）。编译器对 values 原样透传进 __in，类型由字段自身决定。
"""
from __future__ import annotations

# 模块 key（前端 entity）-> { 维度: ORM 字段路径 | True(复合维度) | None }
# unit 维度值为 True = 复合维度标记（见模块 docstring），非 ORM 路径。
MODULE_DIMENSION_FIELDS: dict[str, dict[str, dict | str | bool | None]] = {
    'candidate': {
        'dept': 'referrer__department_id',
        'owner': 'referrer_id',
        'creator': 'created_by_id',
        'unit': True,
        'process': None,
    },
    'demand': {
        'dept': 'department_id',
        'hr': 'hr_id',                                    # 可见：需求主责人
        'owner': 'hr_id',                                 # 隐藏别名（向后兼容存量规则）
        'requested_by': 'requested_by_id',                # 可见：需求提出人
        'sharers': {'kind': 'json_contain', 'field': 'sharers'},
        'hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp'},
        'hiring_manager': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hiring_manager'},
        'hiring_manager_superior': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hiring_manager_superior'},
        'resume_grabber': {'kind': 'reverse', 'field': 'positions__applications__grabbed_by_id'},
        'creator': 'created_by_id',
        'unit': True,
        'process': None,
    },
    'position': {
        'dept': 'department_id',
        'owner': 'owner_id',
        'creator': 'created_by_id',
        'unit': True,
        'process': None,
    },
    'process': {
        'dept': None,
        'owner': None,
        'creator': 'created_by_id',
        'unit': True,
        'process': None,
    },
    'talent': {
        'dept': None,
        'owner': None,
        'creator': 'created_by_id',
        'unit': True,
        'process': None,
    },
}

# 维度元信息（供 options 接口下发前端展示名）。
# contextKeys: 该维度可用的动态值来源（valueSource='dynamic' 时的快捷主体），
#   前端渲染为值模式切换后的首组下拉；键集合与 context_resolvers.DYNAMIC_SOURCE_KEYS 对齐。
#
# 2026-10-15 文案与维度治理（兵哥「部门改为需求部门，负责人拆解为需求中设置的人员字段，
# 创建人改为需求创建人，去掉管理单元」）：
#   - dept/owner/creator 的 label 改为**模块化表述**（需求部门 / 需求负责人 / 需求创建人），
#     消除「部门」在不同模块指向不同实体的歧义（candidate 的 dept 其实是
#     referrer__department_id=推荐人部门，不是候选人本人部门）。
#   - label 必须**按模块分派**：MODULE_DIMENSION_LABELS 优先，缺省回落 DIMENSION_META。
#   - owner 的后端字段路径不变（demand=hr_id，即「需求中设置的人员字段」，与兵哥口径一致）。
DIMENSION_META: dict[str, dict] = {
    'dept': {
        'key': 'dept', 'label': '所属部门', 'valueType': 'department',
        'contextKeys': ['currentUser.departments', 'currentUser.deptSubtree'],
    },
    'owner': {
        'key': 'owner', 'label': '负责人', 'valueType': 'user',
        'contextKeys': ['currentUser.id'],
    },
    'creator': {
        'key': 'creator', 'label': '创建人', 'valueType': 'user',
        'contextKeys': ['currentUser.id'],
    },
    'hr': {'key': 'hr', 'label': '需求主责人', 'valueType': 'user', 'contextKeys': ['currentUser.id']},
    'requested_by': {'key': 'requested_by', 'label': '需求提出人', 'valueType': 'user', 'contextKeys': ['currentUser.id']},
    'sharers': {'key': 'sharers', 'label': '需求共享人', 'valueType': 'user', 'contextKeys': []},
    'hrbp': {'key': 'hrbp', 'label': 'HRBP', 'valueType': 'user', 'contextKeys': []},
    'hiring_manager': {'key': 'hiring_manager', 'label': '用人经理', 'valueType': 'user', 'contextKeys': []},
    'hiring_manager_superior': {'key': 'hiring_manager_superior', 'label': '用人经理上级', 'valueType': 'user', 'contextKeys': []},
    'resume_grabber': {'key': 'resume_grabber', 'label': '简历抢单人', 'valueType': 'user', 'contextKeys': []},
    'unit': {
        'key': 'unit', 'label': '管理单元', 'valueType': 'unit',
        'contextKeys': ['currentUser.managedUnits'],
    },
    'process': {'key': 'process', 'label': '招聘流程', 'valueType': 'process'},
}

# 模块专属维度展示名（优先级高于 DIMENSION_META['label']）。
# 🔴 需求模块（demand）：owner 对应 hr_id（需求单上设置的 HR / 负责人），故叫「需求负责人」；
#    creator 对应 created_by_id，故叫「需求创建人」；dept 对应 department_id，故叫「需求部门」。
MODULE_DIMENSION_LABELS: dict[str, dict[str, str]] = {
    'demand': {
        'dept': '需求部门',
        'creator': '需求创建人',
        'hr': '需求主责人',
    },
}

# 🔴 兵哥拍板：**去掉「管理单元」维度**（2026-10-15）。
# unit 是 M03 复合维度，值为 True 标记、编译期经 iter_unit_scopes 展开为
# 「部门集合 ∪ 成员用户集合」—— 语义上等价于"按管理单元反查可见范围"，但管理员
# 无法直���理解"管理单元"与"部门"的区别，且展开后与其余维度重叠、配置心智负担高。
# 处置：**仅从 UI 下拉隐藏**（前端过滤），后端映射与展开逻辑**全部保留** ——
# 存量规则若已用 unit 维度仍能正常回显与执行（前端按 label 兜底渲染，不静默改语义）。
HIDDEN_DIMENSIONS: dict[str, frozenset[str]] = {
    '*': frozenset({'unit'}),
    'demand': frozenset({'owner'}),
}

# 模块顺序与展示名（抽屉内 5 张卡的顺序）
MODULE_ORDER: list[str] = ['demand', 'process', 'position', 'candidate', 'talent']
MODULE_LABELS: dict[str, str] = {
    'demand': '招聘需求',
    'process': '招聘流程',
    'position': '招聘职位',
    'candidate': '候选人管理',
    'talent': '人才库',
}


def supported_dimensions(entity: str) -> list[str]:
    """返回某模块真实可过滤的维度 key 列表（field 路径非 None 者）。

    unit 是复合维度（值为 True 标记），同样视为已支持 —— 其展开复用本表
    既有的 dept/creator 路径（见 expr_compiler._compile_unit_condition）。
    """
    fields = MODULE_DIMENSION_FIELDS.get(entity, {})
    return [d for d, path in fields.items() if path]


def hidden_dimensions_for(entity: str) -> frozenset[str]:
    """该模块要从 UI 下拉中隐藏的维度（当前全局统一隐藏 unit，见 HIDDEN_DIMENSIONS）。"""
    return HIDDEN_DIMENSIONS.get(entity, frozenset()) | HIDDEN_DIMENSIONS.get('*', frozenset())


def dimension_label(entity: str, dimension: str) -> str:
    """维度展示名：模块专属优先，缺省回落 DIMENSION_META 的通用名。"""
    return (
        MODULE_DIMENSION_LABELS.get(entity, {}).get(dimension)
        or DIMENSION_META.get(dimension, {}).get('label')
        or dimension
    )
