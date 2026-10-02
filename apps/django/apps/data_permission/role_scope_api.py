"""角色级数据权限 API 逻辑（与 RoleViewSet 解耦，便于单测）。

落库契约（零迁移，全部进 DataPermissionRule.scope_payload）：
  - 一个 (role_code, 模块) 一行 ROW 规则；
  - mode=none -> scope_type=NONE  / mode=all -> scope_type=ALL / mode=scope -> scope_type=CUSTOM
    + scope_payload={"expr":<组间>, "groups":[{expr,conditions}]}
  - entity = 模块 key（demand/process/position/candidate/talent）。
"""
from __future__ import annotations

from typing import Dict, List

from django.db import transaction

from .attribute_fields import attribute_fields_for
from .expr_compiler import validate_scope_payload
from .field_map import (
    DIMENSION_META,
    MODULE_LABELS,
    MODULE_ORDER,
    supported_dimensions,
)
from .models import DataPermissionRule

# 单模块选项上限（用户量可能大，前端用虚拟滚动；此处先截取得当数量）
_USER_LIMIT = 1000
_DEPT_LIMIT = 1000


def _department_options() -> List[Dict]:
    from apps.core.models import Department
    return [
        {'id': d.id, 'label': d.name}
        for d in Department.objects.all()[:_DEPT_LIMIT]
    ]


def _user_options() -> List[Dict]:
    from apps.core.models import User
    users = User.objects.all().order_by('id')[:_USER_LIMIT]
    return [{'id': u.id, 'label': u.full_name} for u in users]


def build_modules_response(role) -> Dict:
    """读某角色的全部模块数据权限配置 -> {roleId, roleCode, modules:[...]}。"""
    rules = DataPermissionRule.objects.filter(
        dimension_type='ROLE',
        dimension_value=role.role_code,
        level='ROW',
        entity__in=MODULE_ORDER,
    )
    by_entity = {r.entity: r for r in rules}
    modules = []
    for mk in MODULE_ORDER:
        r = by_entity.get(mk)
        if r is None or r.scope_type == 'ALL':
            mode = 'all'
            expr = ''
            groups = []
        elif r.scope_type == 'NONE':
            mode = 'none'
            expr = ''
            groups = []
        else:  # CUSTOM
            mode = 'scope'
            payload = r.scope_payload or {}
            expr = payload.get('expr', '')
            groups = payload.get('groups', [])
        modules.append({
            'moduleKey': mk,
            'mode': mode,
            'expr': expr,
            'groups': groups,
            'featureGranted': True,  # 数据权限配置本身对超管开放；功能权限耦合后续可接 RolePermissionV2
        })
    return {'roleId': role.id, 'roleCode': role.role_code, 'modules': modules}


def validate_modules(modules: List[Dict]) -> str | None:
    """校验 modules 数组结构 + 每个 scope 模块的 CUSTOM 表达式。返回首个错误原因或 None。"""
    if not isinstance(modules, list):
        return 'modules 必须是数组'
    seen = set()
    for m in modules:
        if not isinstance(m, dict):
            return 'modules 元素格式错误'
        mk = m.get('module_key') or m.get('moduleKey')
        if mk not in MODULE_ORDER:
            return f'未知模块 {mk}'
        if mk in seen:
            return f'模块 {mk} 重复'
        seen.add(mk)
        mode = m.get('mode')
        if mode not in ('none', 'all', 'scope'):
            return f'模块 {mk} 的 mode 非法（应为 none/all/scope）'
        if mode == 'scope':
            payload = {'expr': m.get('expr', ''), 'groups': m.get('groups', [])}
            reason = validate_scope_payload(payload, mk)
            if reason:
                return reason
    return None


@transaction.atomic
def upsert_modules(role, modules: List[Dict], user) -> Dict:
    """先删后建：删除该角色全部 ROW 模块规则，再按 modules 重建。返回最新 modules 配置。"""
    DataPermissionRule.objects.filter(
        dimension_type='ROLE',
        dimension_value=role.role_code,
        level='ROW',
        entity__in=MODULE_ORDER,
    ).delete()
    created_by = getattr(user, 'pk', None)
    for m in modules:
        mk = m.get('module_key') or m.get('moduleKey')
        mode = m.get('mode')
        scope_type = {'none': 'NONE', 'all': 'ALL', 'scope': 'CUSTOM'}[mode]
        payload = None
        if scope_type == 'CUSTOM':
            payload = {'expr': m.get('expr', ''), 'groups': m.get('groups', [])}
        DataPermissionRule.objects.create(
            dimension_type='ROLE',
            dimension_value=role.role_code,
            level='ROW',
            entity=mk,
            scope_type=scope_type,
            scope_payload=payload,
            priority=0,
            status=1,
            created_by=created_by,
        )
    return build_modules_response(role)


def options_payload() -> Dict:
    """模块 × 维度矩阵 + 维度值选项（部门/用户）。"""
    dept_options = _department_options()
    user_options = _user_options()
    modules = []
    for mk in MODULE_ORDER:
        dim_metas = []
        for d in supported_dimensions(mk):
            meta = dict(DIMENSION_META[d])
            if meta['valueType'] == 'department':
                meta['options'] = dept_options
            elif meta['valueType'] == 'user':
                meta['options'] = user_options
            else:
                meta['options'] = []
            dim_metas.append(meta)
        modules.append({
            'moduleKey': mk,
            'label': MODULE_LABELS[mk],
            'dimensions': dim_metas,
            'attributeFields': attribute_fields_for(mk),
        })
    return {'modules': modules}
