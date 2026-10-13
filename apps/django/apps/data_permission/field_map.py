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
MODULE_DIMENSION_FIELDS: dict[str, dict[str, str | bool | None]] = {
    'candidate': {
        'dept': 'referrer__department_id',
        'owner': 'referrer_id',
        'creator': 'created_by_id',
        'unit': True,
        'process': None,
    },
    'demand': {
        'dept': 'department_id',
        'owner': 'hr_id',
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
DIMENSION_META: dict[str, dict] = {
    'dept': {
        'key': 'dept', 'label': '部门', 'valueType': 'department',
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
    'unit': {
        'key': 'unit', 'label': '管理单元', 'valueType': 'unit',
        'contextKeys': ['currentUser.managedUnits'],
    },
    'process': {'key': 'process', 'label': '招聘流程', 'valueType': 'process'},
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
