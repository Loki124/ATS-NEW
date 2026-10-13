"""M06：可见范围预览 / 零命中排查引导 / 管理单元范围完整度。

设计铁律（eval 文档 §7.1 第三批）：预览必须与列表「同源」——
preview_entity_scope 直接调用 scope_filter_q（列表 get_queryset 的唯一真相源），
不做任何二次实现，确保「预览所见 = 列表所得」，杜绝口径漂移（G2 类风险）。

三部分：
1. preview_entity_scope：调用 scope_filter_q，把产出的 Q 解析成结构化摘要，供前端预览卡片。
2. diagnose_zero_hits：列表 0 命中时，依据范围摘要给出排查引导（前端「为什么看不到数据」）。
3. management_unit_completeness：标记管理单元范围是否完整（org_scope / 成员部门 / 成员用户
   任一具备即视为完整，否则提示管理员补充）。
"""
from __future__ import annotations

import logging

from django.db.models import Q

from .scope_resolver import (
    collect_unit_member_depts,
    collect_unit_member_users,
    scope_filter_q,
)

logger = logging.getLogger(__name__)


def describe_scope_q(q: Q | None) -> dict:
    """把 scope_filter_q 产出的 Q 尽力解析为结构化摘要（供前端预览卡片）。

    返回 dict：
      connector         : 'AND' | 'OR' | None
      department_ids    : 可见部门 id 列表（按部门 FK / 创建人部门）
      user_ids          : 可见成员 user id 列表（created_by__in 成员）
      self_only         : 仅自己创建（created_by=<pk>，无部门/成员）
      empty             : 范围为空（pk__in=[]，看不到任何数据）
      recruit_type      : 硬系统分区（social/campus），对所有人生效
      raw               : Q 的字符串，前端兜底展示
    """
    result = {
        'connector': None,
        'department_ids': [],
        'user_ids': [],
        'self_only': False,
        'empty': False,
        'recruit_type': None,
        'raw': str(q) if q is not None else '',
    }
    if q is None:
        return result
    result['connector'] = q.connector
    _walk(q, result)
    return result


def _walk(node: Q, result: dict) -> None:
    children = getattr(node, 'children', None)
    if not children:
        return
    for child in children:
        if isinstance(child, Q):
            _walk(child, result)
            continue
        if isinstance(child, tuple) and len(child) == 2:
            _absorb(child[0], child[1], result)


def _absorb(key, value, result: dict) -> None:
    if key == 'pk__in' and value == []:
        result['empty'] = True
        return
    if key == 'recruit_type':
        result['recruit_type'] = value
        return
    if key.endswith('__in'):
        if 'department' in key:
            result['department_ids'].extend([str(v) for v in (value or [])])
        elif key == 'created_by__in':
            result['user_ids'].extend(list(value or []))
        return
    if key == 'created_by':
        result['user_ids'].append(value)
        result['self_only'] = True


def preview_entity_scope(user, entity: str, app_code: str | None = None,
                         recruit_type: str | None = None) -> dict:
    """预览某实体对当前用户的有效可见范围（与列表同源：直接调 scope_filter_q）。

    返回 describe_scope_q 的增强摘要，附带：
      custom_replaced : 是否命中角色自定义范围（替换了默认 scope）
      is_super_admin  : 是否超管（全量）
      all_data        : 是否无行级限制（全量可见）
    """
    q = scope_filter_q(user, app_code=app_code, recruit_type=recruit_type, entity=entity)
    desc = describe_scope_q(q)

    try:
        from apps.data_permission.enforcement import role_entity_scope_q
        custom_q = role_entity_scope_q(user, entity)
    except Exception:  # noqa: BLE001 — 自定义范围探测失败不阻断预览
        custom_q = None
    desc['custom_replaced'] = custom_q is not None

    try:
        from apps.core.role_v2_query import is_super_admin
        desc['is_super_admin'] = bool(user) and is_super_admin(user)
    except Exception:  # noqa: BLE001 — 超管判定失败按非超管处理, 不阻断预览
        desc['is_super_admin'] = False

    desc['all_data'] = (
        not desc['department_ids']
        and not desc['user_ids']
        and not desc['empty']
        and not desc['custom_replaced']
    )
    return desc


def diagnose_zero_hits(desc: dict) -> list[str]:
    """列表 0 命中时给出排查引导（依据范围摘要，前端「为什么看不到数据」文案）。"""
    hints: list[str] = []
    if desc.get('empty'):
        hints.append('当前可见范围为空：未配置任何数据范围，请联系管理员设置管理单元的部门/成员。')
    elif desc.get('self_only'):
        hints.append('当前仅可见「自己创建」的数据：请确认你的管理单元是否已配置部门或成员范围。')
    elif desc.get('department_ids'):
        hints.append(
            f'当前仅可见部门 {desc["department_ids"]} 的数据：'
            '如需更多，请联系管理员扩大管理单元范围。'
        )
    elif desc.get('user_ids'):
        hints.append('当前仅可见指定成员的数据：可联系管理员扩大范围。')
    if desc.get('custom_replaced'):
        hints.append('已应用角色自定义数据范围：请联系管理员调整该角色的可见范围规则。')
    if desc.get('recruit_type'):
        hints.append(f'当前按招聘类型「{desc["recruit_type"]}」分区隔离，社会/校园数据互不可见。')
    if not hints:
        hints.append('当前无可见范围限制却仍 0 命中，可能是数据本身为空，或筛选条件过严。')
    return hints


def management_unit_completeness(unit_ids) -> dict:
    """标记管理单元范围是否完整（org_scope / 成员部门 / 成员用户 任一具备即完整）。

    返回 {unit_id: {has_org_scope, member_dept_count, member_user_count, complete}}。
    """
    from .models_permission_v2 import ManagementUnit

    out: dict = {}
    for u in ManagementUnit.objects.filter(id__in=list(unit_ids), status=1):
        org = getattr(u, 'org_scope', None)
        has_org = bool(org)
        try:
            member_depts = collect_unit_member_depts([u.id]) or []
        except Exception:  # noqa: BLE001 — 成员解析失败按空处理, 不影响完整度判定
            member_depts = []
        try:
            member_users = collect_unit_member_users([u.id]) or []
        except Exception:  # noqa: BLE001 — 成员解析失败按空处理, 不影响完整度判定
            member_users = []
        complete = has_org or bool(member_depts) or bool(member_users)
        out[u.id] = {
            'has_org_scope': has_org,
            'member_dept_count': len(member_depts),
            'member_user_count': len(member_users),
            'complete': complete,
        }
    return out
