"""实体行级数据范围（Scope）配置 —— 单一真相源。

背景 (2026-10-08 审查):
    每个 ViewSet 各自声明 `scope_field` / `scope_creator_field`, 而导出、批量操作等
    非 ViewSet 入口拿不到这两个属性, 于是干脆 `Model.objects.all()` 全表查 ——
    「列表页看不到的数据, 换个接口就能导出/修改」。

本模块把「实体 → (scope_field, creator_field)」的映射集中成一张表, 供
ViewSet 之外的入口复用, 避免导出与列表两套口径漂移。

⚠️ 约定: 新增实体时**必须**同时登记到这里和各 ViewSet; ViewSet 的
   scope_field / scope_creator_field 应与本表保持一致 (tests/test_entity_scope.py
   会断言两边不漂移)。
"""
from __future__ import annotations

from django.db.models import QuerySet

from apps.core.scope_resolver import scope_filter_q

# entity -> (scope_field, creator_field)
# 取值与各 ViewSet 上的 scope_field / scope_creator_field 逐一对应。
ENTITY_SCOPE: dict[str, dict[str, str]] = {
    'candidate': {'scope_field': 'referrer__department', 'creator_field': 'created_by'},
    'application': {'scope_field': 'position__department', 'creator_field': 'created_by'},
    'demand': {'scope_field': 'department', 'creator_field': 'requested_by'},
    'position': {'scope_field': 'department', 'creator_field': 'created_by'},
    'offer': {'scope_field': 'position__department', 'creator_field': 'created_by'},
    'interview': {'scope_field': 'application__position__department', 'creator_field': 'created_by'},
    'onboarding': {'scope_field': 'position__department', 'creator_field': 'created_by'},
    'invitation': {'scope_field': 'application__position__department', 'creator_field': 'inviter'},
    'talent_pool': {'scope_field': 'last_position__department', 'creator_field': 'created_by'},
    'referral': {'scope_field': 'referrer__department', 'creator_field': 'referrer'},
    # --- 校招域（2026-10-19 需求 1-2「各个角色数据相互隔离」）---
    # 校招实体此前完全未登记 → entity_scope_q 显式 KeyError，导出/批量等非 ViewSet 入口
    # 无范围配置，导致「列表看不到的数据换个接口就能导出/改」。
    # 本次先登记「确有部门承载字段」的三类实体；campus_person 推迟到 S5-10。
    #
    # scope_field 口径（必须指向模型上承载 Department id 的字段，否则 __in 过滤失效/FieldError）：
    #   campus_class       经 hrbp（班级 HRBP）带出部门 —— ClassRoom.hrbp 是 User FK，
    #                       User.department 是 Department FK → hrbp__department 合法。
    #   campus_resource    bu 是 Department FK（归属 BU = 二级部门）→ bu 合法。
    #   campus_arrangement current_dept 是 Department FK（当前轮岗部门）→ 合法。
    #
    # ⚠️ campus_person 暂不登记：Person 当前无部门承载字段 —— Person.bu 是 CharField choices
    #   （BU 类别代码，非 Department.id），head_teacher / class_room 等关系字段要到 S5-10
    #   才新增。强行登记只能写空串 scope_field，既通不过 tests/test_entity_scope.py 的
    #   「每实体必须有非空 scope_field」断言，又会在 S5-03 接入后触发 FieldError。
    #   S5-10 落地 Person.head_teacher / Person.class_room 后，再补
    #   'campus_person': {'scope_field': 'head_teacher__department', ...} 与
    #   MODULE_DIMENSION_FIELDS['campus_person'] 的 head_teacher / campus_class 维度。
    # ↑ 上段为 S5-02 当时的前置未就绪记录；S5-10 已落地 Person.head_teacher（User FK）
    #   与 Person.class_room（ClassRoom FK），前置现已就绪 —— 2026-10-21 S5-24 补登记。
    #   scope_field 口径：head_teacher__department —— 班主任（User FK）→ User.department
    #   （Department FK），合法路径；无班主任时该维度为空（回退 creator SELF）。
    'campus_class': {'scope_field': 'hrbp__department', 'creator_field': 'created_by'},
    'campus_resource': {'scope_field': 'bu', 'creator_field': 'created_by'},
    'campus_arrangement': {'scope_field': 'current_dept', 'creator_field': 'created_by'},
    'campus_person': {'scope_field': 'head_teacher__department', 'creator_field': 'created_by'},
}


def entity_scope_q(request, entity: str, model=None):
    """构造当前用户对某类实体的行级可见范围 Q。

    model: 可选。用于判断该模型是否有 recruit_type 字段 —— 招聘类型分区是 opt-in,
    对 Onboarding 这类没有该字段的模型不能硬加, 否则 FieldError
    (与 ScopeQuerysetMixin 的 hasattr 守卫保持一致)。
    """
    cfg = ENTITY_SCOPE.get(entity)
    if cfg is None:
        # 未登记实体 — 显式报错, 绝不静默放行全表
        raise KeyError(
            f'实体 {entity!r} 未在 ENTITY_SCOPE 登记。请补充其 '
            'scope_field / creator_field, 否则会退化为全表可见。'
        )
    rt = getattr(request, 'recruit_type', 'social')
    if model is not None and not hasattr(model, 'recruit_type'):
        rt = None
    return scope_filter_q(
        request.user,
        app_code='recruit',
        scope_field=cfg['scope_field'],
        creator_field=cfg['creator_field'],
        recruit_type=rt,
        entity=entity,
    )


def scoped_queryset(request, queryset: QuerySet, entity: str) -> QuerySet:
    """按当前用户的数据范围过滤 queryset。"""
    return queryset.filter(
        entity_scope_q(request, entity, model=queryset.model)
    )
