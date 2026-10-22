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
# spec 形状（见 docs/DESIGN_数据权限规则弹窗选项表.md §0）：
#   · 裸字符串      -> 普通列 / 正向 FK 路径（复用 static __in 分支，零新增编译器代码）
#   · {'kind':'dfv','resource','field_key','via'} -> DynamicFieldValue 人员维度（hrbp 等）
#     `via` = 「实体 → Demand」的 ORM 路径；实体自身即 Demand 时 via=''
#   · {'kind':'path','field'} -> 跨表反向 FK 多值路径（统一 Q(pk__in=Subquery) 收口，
#     杜绝 Candidate/Application 多对多 fan-out）
#   · {'kind':'json_contain','field'} -> JSON 数组列（sharers）
#   · {'kind':'lock_owner'} -> 简历锁定人复合条件 + 空值运算符
MODULE_DIMENSION_FIELDS: dict[str, dict[str, dict | str | bool | None]] = {
    'candidate': {
        # —— 兵哥表可见 9 项（2026-10-15）——
        'uploaded_by': 'uploaded_by_id',                          # 简历上传人（正向 FK，无 fan-out）
        'referrer': 'referrer_id',                                # 简历推荐人
        'lock_owner': {'kind': 'lock_owner'},                     # 简历锁定人（复合 + 空值）
        'demand_tbp': {'kind': 'path', 'field': 'applications__position__demand__hr_id'},
        'demand_hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp', 'via': 'applications__position__demand'},
        'demand_creator': {'kind': 'path', 'field': 'applications__position__demand__created_by_id'},
        'position_tbp': {'kind': 'path', 'field': 'applications__position__demand__hr_id'},
        'position_hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp', 'via': 'applications__position__demand'},
        'position_creator': {'kind': 'path', 'field': 'applications__position__created_by_id'},
        # —— 既有维度，UI 隐藏、后端保留兼容（存量规则仍可编译）——
        'creator': 'created_by_id',
        'dept': 'referrer__department_id',
        'owner': 'referrer_id',                                   # 隐藏别名（旧 = referrer_id）
        'unit': True,
        'process': None,
    },
    'demand': {
        # —— 兵哥表可见 9 项（2026-10-15 兵哥：需求人员字段不止 创建人/TBP/HRBP，全部补全）——
        'tbp': 'hr_id',                                           # TBP（需求主负责人）
        'hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp', 'via': ''},
        'creator': 'created_by_id',                                # 需求创建人
        'dept': 'department_id',                                   # 需求部门
        'requested_by': 'requested_by_id',                         # 需求提出人
        'sharers': {'kind': 'json_contain', 'field': 'sharers'},   # 需求共享人
        'hiring_manager': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hiring_manager', 'via': ''},  # 用人经理
        'hiring_manager_superior': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hiring_manager_superior', 'via': ''},  # 用人经理上级
        'resume_grabber': {'kind': 'path', 'field': 'positions__applications__grabbed_by_id'},  # 简历抢单人
        # —— UI 隐藏、后端保留兼容（存量规则）：owner/hr 为 tbp 的冗余别名 ——
        'owner': 'hr_id',                                          # 隐藏别名（向后兼容旧 owner 规则）
        'hr': 'hr_id',                                             # 隐藏别名（向后兼容旧 hr 规则）
        'unit': True,
        'process': None,
    },
    'position': {
        # —— 兵哥表可见 4 项（2026-10-15）——
        'tbp': 'demand__hr_id',                                    # TBP（= 其 demand 的 hr）
        'hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp', 'via': 'demand'},
        'creator': 'created_by_id',                                # 职位创建人
        'dept': 'department_id',                                   # 职位部门
        # —— UI 隐藏、后端保留兼容（存量规则）——
        'owner': 'owner_id',                                       # 隐藏别名
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
    # ==========================================================================
    # 校招域（2026-10-19 需求 1-2「各个角色数据相互隔离」，S5-02）
    # ==========================================================================
    # 🔴 校招实体此前完全缺席 → role_entity_scope_q 拿不到 CUSTOM 规则，
    #    「带教导师只看自己带的」「班主任只看本班」这类按人/按班的隔离无处表达，
    #    只能回退默认 scope（部门/SELF）。本组登记是 B0 的核心交付。
    #
    # ⚠️ 本次仅登记确有部门承载字段的三类实体；campus_person 因 Person 无部门字段
    #    （bu 是 CharField choices，head_teacher/class_room 待 S5-10 新增）推迟登记，
    #    详见下方 campus_class 块后的注释。
    #
    # dept 取值口径（Department.pk 为 CharField，FK 直接给 id 空间）：
    #   campus_arrangement  current_dept —— 当前轮岗部门，最贴近「谁管这条安排」
    #   campus_resource      bu          —— 归属 BU（BU = 二级部门）
    #   campus_class         hrbp__department —— ClassRoom 自身无 department FK，
    #                                    经 HRBP 用户带出部门
    # hrbp/head_teacher/mentor/campus_class 四个用户/班级维度供 CUSTOM 规则使用，
    # 均可直接编译为 Q(head_teacher_id__in=[当前用户 id]) 这类精确条件。
    'campus_arrangement': {
        'dept': 'current_dept_id',
        'owner': 'mentor_id',
        'creator': 'created_by_id',
        'hrbp': 'class_room__hrbp_id',
        'head_teacher': 'head_teacher_id',
        'mentor': 'mentor_id',
        # 2026-10-21 S5-35：班长（class_monitor，2026-10-21 三期新增于
        # RotationArrangement）。⚠️ 与 D-02 的区别：D-02 删的是 ClassRoom.class_monitor
        # （个人档案不再维护班长）；此处是**轮岗安排**上的班长归属，字段真实存在，
        # 故可作为按人隔离维度（编译为 Q(class_monitor_id__in=[...]））。
        'class_monitor': 'class_monitor_id',
        'campus_class': 'class_room_id',
        'unit': True,
        'process': None,
    },
    'campus_resource': {
        'dept': 'bu_id',
        'owner': None,
        'creator': 'created_by_id',
        'unit': True,
        'process': None,
    },
    'campus_class': {
        'dept': 'hrbp__department_id',
        'owner': 'hrbp_id',
        'creator': 'created_by_id',
        'hrbp': 'hrbp_id',
        'head_teacher': 'head_teacher_id',
        'unit': True,
        'process': None,
    },
    # ⚠️ campus_person 暂不登记（与 ENTITY_SCOPE 同步推迟到 S5-10）：Person 当前无部门承载
    #   字段（bu 是 CharField choices，head_teacher/class_room 待 S5-10 新增）。S5-10 落地后
    #   在此补 'campus_person': {'dept': 'head_teacher__department_id', 'head_teacher': 'head_teacher_id',
    #   'campus_class': 'class_room_id', 'creator': 'created_by_id', 'unit': True, 'process': None}。
    # ↑ 上段为 S5-02 当时的前置未就绪记录；S5-10 已落地 Person.head_teacher（User FK）
    #   与 Person.class_room（ClassRoom FK），前置现已就绪 —— 2026-10-21 S5-24 补登记。
    #   维度口径：
    #     dept       head_teacher__department_id —— 经班主任带出部门
    #     head_teacher head_teacher_id           —— 班主任「只看本班」
    #     campus_class class_room_id             —— 经班级维度（与 campus_arrangement 同构）
    #     hrbp       class_room__hrbp_id         —— 经班级 HRBP（「HRBP 看本部门及下级」）
    'campus_person': {
        'dept': 'head_teacher__department_id',
        'owner': None,
        'creator': 'created_by_id',
        'hrbp': 'class_room__hrbp_id',
        'head_teacher': 'head_teacher_id',
        'campus_class': 'class_room_id',
        'unit': True,
        'process': None,
    },
}

# 维度元信息（供 options 接口下发前端展示名 + 运算符 + 动态源）。
# contextKeys: 该维度可用的动态值来源（valueSource='dynamic' 时的快捷主体），
#   前端渲染为值模式切换后的首组下拉；键集合与 context_resolvers.DYNAMIC_SOURCE_KEYS 对齐。
# operators: 该维度可用的运算符（前端据其渲染运算符下拉）。
#   - 用户类维度：包含 / 不包含（+ 简历锁定人额外支持 为空 / 不为空）
#   - 部门类维度：不在此下发 operators，前端按其 valueType=department 走内置
#     UNIFIED_DEPT_OPERATORS（属于 / 不属于 / 含下级 组合），与既有关系词模型一致。
# 仅「可见」维度需在此登记 operators；隐藏维度仅保留 meta 作 label 兜底（前端不下发）。
DIMENSION_META: dict[str, dict] = {
    # —— 部门类（valueType=department，运算符走前端内置 UNIFIED_DEPT_OPERATORS）——
    'dept': {
        'key': 'dept', 'label': '部门', 'valueType': 'department',
        'contextKeys': ['currentUser.departments', 'currentUser.deptSubtree'],
    },
    # —— 用户类（包含 / 不包含 + 动态 currentUser.id）——
    'creator': {
        'key': 'creator', 'label': '创建人', 'valueType': 'user',
        'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'tbp': {
        'key': 'tbp', 'label': 'TBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'hrbp': {
        'key': 'hrbp', 'label': 'HRBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'uploaded_by': {
        'key': 'uploaded_by', 'label': '简历上传人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'referrer': {
        'key': 'referrer', 'label': '简历推荐人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'demand_tbp': {
        'key': 'demand_tbp', 'label': '所属需求的TBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'demand_hrbp': {
        'key': 'demand_hrbp', 'label': '所属需求的HRBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'demand_creator': {
        'key': 'demand_creator', 'label': '所属需求的需求创建人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'position_tbp': {
        'key': 'position_tbp', 'label': '所属职位的TBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'position_hrbp': {
        'key': 'position_hrbp', 'label': '所属职位的HRBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'position_creator': {
        'key': 'position_creator', 'label': '所属职位的职位创建人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    # —— 简历锁定人（额外支持空值）——
    'lock_owner': {
        'key': 'lock_owner', 'label': '简历锁定人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [
            {'value': 'in', 'label': '包含'},
            {'value': 'not_in', 'label': '不包含'},
            {'value': 'is_empty', 'label': '为空'},
            {'value': 'is_not_empty', 'label': '不为空'},
        ],
    },
    # —— 需求模块补充人员维度（2026-10-15 兵哥：需求人员字段不止 创建人/TBP/HRBP）——
    # 这些维度在 demand 模块**可见**，与 tbp/hrbp/creator 同等对待：
    # 统一「包含/不包含」运算符 + 「当前登录用户」动态源。
    'requested_by': {
        'key': 'requested_by', 'label': '需求提出人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'sharers': {
        'key': 'sharers', 'label': '需求共享人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'hiring_manager': {
        'key': 'hiring_manager', 'label': '用人经理', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'hiring_manager_superior': {
        'key': 'hiring_manager_superior', 'label': '用人经理上级', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'resume_grabber': {
        'key': 'resume_grabber', 'label': '简历抢单人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    # —— 隐藏维度：保留 meta 仅作 label 兜底（owner/hr 为 tbp 的冗余别名，UI 不下发）——
    'owner': {'key': 'owner', 'label': '负责人', 'valueType': 'user', 'contextKeys': ['currentUser.id']},
    'hr': {'key': 'hr', 'label': '需求主责人', 'valueType': 'user', 'contextKeys': ['currentUser.id']},
    'unit': {
        'key': 'unit', 'label': '管理单元', 'valueType': 'unit',
        'contextKeys': ['currentUser.managedUnits'],
    },
    'process': {'key': 'process', 'label': '招聘流程', 'valueType': 'process'},
    # —— 校招域维度（2026-10-19 S5-02，配合 MODULE_DIMENSION_FIELDS 校招四实体）——
    # 用户类维度，与 creator/hrbp 同款「包含/不包含」+ currentUser.id 动态源；
    # 承载需求 1-2「带教导师只看自己带的 / 班主任只看本班」这类按人隔离规则。
    'head_teacher': {
        'key': 'head_teacher', 'label': '班主任', 'valueType': 'user',
        'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    'mentor': {
        'key': 'mentor', 'label': '带教导师', 'valueType': 'user',
        'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    # —— 校招域：班长（2026-10-21 S5-35）——
    # 与 head_teacher / mentor 同属用户类维度：静态「包含/不包含」固定人员，
    # 或动态「当前登录用户」（编译器编译为 Q(class_monitor_id__in=[user.pk])）。
    'class_monitor': {
        'key': 'class_monitor', 'label': '班长', 'valueType': 'user',
        'contextKeys': ['currentUser.id'],
        'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}],
    },
    # 班级维度：valueType 非 user/department，用 str 承载班级 id。
    # 编译器对裸字符串走 static __in 分支（见模块 docstring spec 形状说明）。
    'campus_class': {
        'key': 'campus_class', 'label': '班级', 'valueType': 'string',
        'contextKeys': [], 'operators': [{'value': 'in', 'label': '包含'}],
    },
}

# 模块专属维度展示名（优先级高于 DIMENSION_META['label']）。
# 🔴 需求/职位模块：TBP 对应 hr_id（需求单上设置的 HR / 主负责人），故叫「TBP（需求主负责人）」；
#    creator 对应 created_by_id，故叫「需求创建人 / 职位创建人」；dept 对应 department_id，故叫「需求部门」。
MODULE_DIMENSION_LABELS: dict[str, dict[str, str]] = {
    'demand': {
        'dept': '需求部门',
        'creator': '需求创建人',
        'tbp': 'TBP（需求主负责人）',
        'hrbp': 'HRBP',
        # 2026-10-15 兵哥：需求人员字段全部补全可见（命名严格按兵哥表格，禁止简写）
        'requested_by': '需求提出人',
        'sharers': '需求共享人',
        'hiring_manager': '用人经理',
        'hiring_manager_superior': '用人经理上级',
        'resume_grabber': '简历抢单人',
    },
    'position': {
        'dept': '需求部门',
        'creator': '职位创建人',
        'tbp': 'TBP（需求主负责人）',
        'hrbp': 'HRBP',
    },
    'candidate': {
        'uploaded_by': '简历上传人',
        'referrer': '简历推荐人',
        'lock_owner': '简历锁定人',
        'demand_tbp': '所属需求的TBP',
        'demand_hrbp': '所属需求的HRBP',
        'demand_creator': '所属需求的需求创建人',
        'position_tbp': '所属职位的TBP',
        'position_hrbp': '所属职位的HRBP',
        'position_creator': '所属职位的职位创建人',
    },
    # 校招域（2026-10-19 S5-02）：与 DIMENSION_META['label'] 同值，此处登记是为
    # 保持「每个已登记实体都有专属标签项」的一致性，便于后续按模块覆写显示名。
    'campus_arrangement': {
        'dept': '当前轮岗部门',
        'creator': '创建人',
        'hrbp': '员工HRBP',
        'head_teacher': '班主任',
        'mentor': '导师',
        'class_monitor': '班长',
        'campus_class': '班级',
    },
    'campus_resource': {
        'dept': '归属BU',
        'creator': '创建人',
    },
    'campus_class': {
        'dept': 'HRBP所在部门',
        'creator': '创建人',
        'hrbp': '班级HRBP',
        'head_teacher': '班主任',
    },
    'campus_person': {
        'dept': '所属部门',
        'creator': '创建人',
    },
}

# 🔴 兵哥拍板：**去掉「管理单元」维度**（2026-10-15）。
# unit 是 M03 复合维度，值为 True 标记、编译期经 iter_unit_scopes 展开为
# 「部门集合 ∪ 成员用户集合」—— 语义上等价于"按管理单元反查可见范围"，但管理员
# 无法直���理解"管理单元"与"部门"的区别，且展开后与其余维度重叠、配置心智负担高。
# 处置：**仅从 UI 下拉隐藏**（前端过滤），后端映射与展开逻辑**全部保留** ——
# 存量规则若已用 unit 维度仍能正常回显与执行（前端按 label 兜底渲染，不静默改语义）。
#
# 2026-10-15 维度治理（兵哥弹窗选项表）：
#  - 需求模块：TBP/HRBP/创建人/提出人/共享人/用人经理/用人经理上级/抢单人 **全部可见**
#    （兵哥明确"人员字段不止 创建人/TBP/HRBP，需补全"）；仅 owner/hr（tbp 的冗余别名）隐藏。
#  - 候选人：改用 uploaded_by/referrer/lock_owner/demand_*/position_*，creator/dept/owner 隐藏。
#  - 职位：tbp/hrbp/creator/dept 可见，owner 隐藏。
HIDDEN_DIMENSIONS: dict[str, frozenset[str]] = {
    '*': frozenset({'unit'}),
    # 2026-10-15 兵哥：需求人员字段不止 创建人/TBP/HRBP —— 提出人/共享人/用人经理/
    # 用人经理上级/抢单人 全部改为**可见**；仅 owner/hr（tbp 的冗余别名）继续隐藏。
    'demand': frozenset({'owner', 'hr'}),
    'candidate': frozenset({'owner', 'creator', 'dept'}),
    'position': frozenset({'owner'}),
    # 2026-10-21 S5-35：校招生管理卡只暴露**人员关系四维度**
    # （员工HRBP / 班长 / 班主任 / 导师），与需求一致 —— 这四个维度构成校招域
    # 「按人隔离」的完整语义（见方案 §2.2 隔离矩阵）。
    # 隐藏项及原因：
    #   owner       —— 与 mentor 同指 mentor_id（冗余别名），同 demand/position 处理；
    #   campus_class—— valueType='string' 且**无值选项源**（options_payload 对非
    #                  user/department/unit 一律下发空 options），下拉会是空控件；
    #   dept        —— 部门类维度走 UNIFIED_DEPT_OPERATORS（属于/不属于/含下级），
    #                  与本卡要求的「包含/不包含」运算符族不同；部门隔离已由
    #                  默认 scope（scope_field='current_dept'）覆盖，不需自定义规则；
    #   creator     —— 同上，创建人隔离由默认 scope 的 SELF 兜底覆盖。
    # ⚠️ 隐藏只影响 UI 下拉（options_payload 不下发），后端映射与编译逻辑全部保留 ——
    #    存量规则若引用这些维度仍能正常编译执行（与既有 hidden 维度同策略）。
    'campus_arrangement': frozenset({'owner', 'campus_class', 'dept', 'creator'}),
}

# 模块顺序与展示名（抽屉内的卡片顺序）
MODULE_ORDER: list[str] = [
    'demand', 'process', 'position', 'candidate', 'talent',
    # 2026-10-21 S5-35：校招生管理独立卡（排在校招域之后，与「校招生管理」一级
    # 导航分组对应）。实体键 = campus_arrangement，原因见 MODULE_LABELS 注释。
    'campus_arrangement',
]
MODULE_LABELS: dict[str, str] = {
    'demand': '招聘需求',
    'process': '招聘流程',
    'position': '招聘职位',
    'candidate': '候选人管理',
    'talent': '人才库',
    # 2026-10-21 S5-35：校招域独立配置卡。
    # ⚠️ 实体键 = campus_arrangement（轮岗安排）——**不是**整个校招域的合并视图：
    #   校招四实体（campus_person/campus_class/campus_resource/campus_arrangement）
    #   各自对应一个 ViewSet 的 data_perm_entity，规则按 entity 精确匹配执行，
    #   一张卡只能治理一个实体（DataPermissionRule.entity 是单值字段）。
    #   选 campus_arrangement 的理由：本次要求的四个维度（员工HRBP / 班长 / 班主任 /
    #   导师）**只有它全部具备** —— class_monitor（班长）字段仅存在于
    #   RotationArrangement（2026-10-21 三期新增），campus_person 侧无此字段。
    'campus_arrangement': '校招生管理',
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
