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

from .attribute_fields import SCENARIO_ROW_FILTER, attribute_fields_for
from .expr_compiler import validate_scope_payload
from .field_map import (
    DIMENSION_META,
    MODULE_LABELS,
    MODULE_ORDER,
    supported_dimensions,
)
from .models import DataPermissionRule
from .scope_templates import summarize_drift

# 单模块选项上限（用户量可能大，前端用虚拟滚动；此处先截取得当数量）
_USER_LIMIT = 1000
_DEPT_LIMIT = 1000
_UNIT_LIMIT = 500


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


def _unit_options() -> List[Dict]:
    """管理单元选项（unit 复合维度静态值域, M03）。

    空壳检测（护栏一, 非阻断）：判定与编译期 expr_compiler._compile_unit_condition
    同源 —— 以 iter_unit_scopes 的单单元展开为准，org_scope 展开 ∪ 成员展开
    均为空（has_all 除外）即空壳，配了也看不到任何数据。此处仅打 emptyShell
    标记供前端提示，**不阻断保存**：先建单元、后配范围是合法中间态。
    """
    from apps.core.models_permission_v2 import ManagementUnit
    from apps.core.scope_resolver import iter_unit_scopes

    units = list(
        ManagementUnit.objects.filter(status=1)
        .order_by('display_order', 'id')[:_UNIT_LIMIT]
    )
    options: List[Dict] = []
    for u in units:
        opt: Dict = {'id': u.id, 'label': u.unit_name, 'parentId': u.parent_id}
        scopes = list(iter_unit_scopes([u.id], app_code='recruit'))
        if scopes:
            dept_ids, user_ids, _org_dr, _person_dr, has_all = scopes[0]
            if not has_all and not dept_ids and not user_ids:
                opt['emptyShell'] = True
        options.append(opt)
    return options


def _collect_template_drifts(modules: List[Dict]) -> Dict[str, List[Dict]]:
    """汇总各模块的权限模板版本漂移 -> {moduleKey: [漂移标记]}。

    为什么需要：模板引用是**快照语义**（改模板不影响在用规则），所以规则页
    必须显式告诉管理员「你引用的模板出新版本了」，否则模板改了也没人知道，
    快照就变成了没人维护的历史包袱。

    漂移有两种：
      - outdated: 模板已升版本，快照落后 -> 提示可升级（需人工确认，不自动改语义）
      - missing : 模板被软删 -> 仅告知，引用仍按快照正常执行

    只查一次模板表；无任何 templateRef 时直接返回空，不产生查询。
    """
    codes: set = set()
    for m in modules:
        if m.get('mode') != 'scope':
            continue
        for g in (m.get('groups') or []):
            ref = (g or {}).get('templateRef') or {}
            if isinstance(ref, dict) and ref.get('templateCode'):
                codes.add(ref['templateCode'])
        # v2: 写范围条件组同样可引用模板（快照语义同读范围）
        wm = m.get('write') or {}
        if wm.get('mode') == 'scope':
            for g in (wm.get('groups') or []):
                ref = (g or {}).get('templateRef') or {}
                if isinstance(ref, dict) and ref.get('templateCode'):
                    codes.add(ref['templateCode'])
    if not codes:
        return {}

    from .models import DataPermTemplate

    # all_objects: 软删的模板也要能判定为 missing，而不是「查不到就当没有」
    lookup = {t.code: t for t in DataPermTemplate.all_objects.filter(code__in=codes)}

    out: Dict[str, List[Dict]] = {}
    for m in modules:
        drifts: List[Dict] = []
        if m.get('mode') == 'scope':
            drifts.extend(summarize_drift(m.get('groups') or [], lookup))
        wm = m.get('write') or {}
        if wm.get('mode') == 'scope':
            drifts.extend(summarize_drift(wm.get('groups') or [], lookup))
        if drifts:
            out[m['moduleKey']] = drifts
    return out


def build_modules_response(role) -> Dict:
    """读某角色的全部模块数据权限配置 -> {roleId, roleCode, modules:[...]}。

    v2：每模块返回 read 配置（mode/expr/groups，row_access=NULL 行）+ write 配置
    （write: {mode, expr, groups, actions}，row_access=WRITE 行；无 WRITE 行时
    write.mode='none' = 未配置写范围 = 沿用功能权限，前端显式展示该语义）。
    """
    rules = DataPermissionRule.objects.filter(
        dimension_type='ROLE',
        dimension_value=role.role_code,
        level='ROW',
        entity__in=MODULE_ORDER,
    )
    read_by_entity: Dict[str, DataPermissionRule] = {}
    write_by_entity: Dict[str, DataPermissionRule] = {}
    for r in rules:
        if r.row_access == 'WRITE':
            write_by_entity[r.entity] = r
        else:
            read_by_entity[r.entity] = r

    modules = []
    for mk in MODULE_ORDER:
        # ---- 读范围（存量语义不变）----
        r = read_by_entity.get(mk)
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

        # ---- 写范围（v2）----
        w = write_by_entity.get(mk)
        if w is None or w.scope_type == 'NONE':
            write_view: Dict = {'mode': 'none', 'expr': '', 'groups': [], 'actions': []}
        elif w.scope_type == 'ALL':
            write_view = {'mode': 'all', 'expr': '', 'groups': [], 'actions': list(w.actions or [])}
        elif w.scope_type == 'OWNER':
            write_view = {'mode': 'owner', 'expr': '', 'groups': [], 'actions': list(w.actions or [])}
        else:  # CUSTOM
            wp = w.scope_payload or {}
            write_view = {
                'mode': 'scope',
                'expr': wp.get('expr', ''),
                'groups': wp.get('groups', []),
                'actions': list(w.actions or []),
            }

        modules.append({
            'moduleKey': mk,
            'mode': mode,
            'expr': expr,
            'groups': groups,
            'featureGranted': True,  # 数据权限配置本身对超管开放；功能权限耦合后续可接 RolePermissionV2
            'templateDrifts': [],   # 由下方统一填充（避免逐模块查模板表）
            'write': write_view,
        })

    drifts = _collect_template_drifts(modules)
    for m in modules:
        m['templateDrifts'] = drifts.get(m['moduleKey'], [])

    return {'roleId': role.id, 'roleCode': role.role_code, 'modules': modules}


# 写范围 mode -> RowScopeType（v2）。none 不建 WRITE 行。
_WRITE_MODE_TO_SCOPE = {'all': 'ALL', 'owner': 'OWNER', 'scope': 'CUSTOM'}


def _validate_write_block(mk: str, write: object) -> str | None:
    """校验单模块 write 子结构。返回首个错误原因或 None。"""
    if write is None:
        return None  # 不带 write = 不配置写范围（向后兼容旧 payload）
    if not isinstance(write, dict):
        return f'模块 {mk} 的 write 必须是对象'
    mode = write.get('mode', 'none')
    if mode not in ('none', 'all', 'owner', 'scope'):
        return f'模块 {mk} 的 write.mode 非法（应为 none/all/owner/scope）'
    if mode == 'none':
        return None
    actions = write.get('actions')
    # 配置了写范围（非 none）必须显式给出动作集合 —— 缺省拒绝是 fail-closed 的前提：
    # 不允许「配了范围却忘了勾动作」这种被静默解释成全拒/全放的歧义配置。
    if not isinstance(actions, list) or not actions:
        return f'模块 {mk} 配置了写范围（mode={mode}）但未提供 actions'
    from .action_registry import validate_write_actions
    reason = validate_write_actions(actions)
    if reason:
        return f'模块 {mk}: {reason}'
    if mode == 'scope':
        payload = {'expr': write.get('expr', ''), 'groups': write.get('groups', [])}
        reason = validate_scope_payload(payload, mk)
        if reason:
            return f'模块 {mk} 写范围: {reason}'
    return None


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
        reason = _validate_write_block(mk, m.get('write'))
        if reason:
            return reason
    return None


@transaction.atomic
def upsert_modules(role, modules: List[Dict], user) -> Dict:
    """先删后建：删除该角色全部 ROW 模块规则（含 WRITE 行），再按 modules 重建。

    v2：每模块最多建两行 —— 读范围（row_access=NULL，与存量一致）+
    写范围（row_access=WRITE，仅当 write.mode != 'none' 时）。
    返回最新 modules 配置。
    """
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
        # ---- v2 写范围行 ----
        write = m.get('write') or {}
        w_mode = write.get('mode', 'none')
        if w_mode == 'none':
            continue
        w_scope_type = _WRITE_MODE_TO_SCOPE[w_mode]
        w_payload = None
        if w_scope_type == 'CUSTOM':
            w_payload = {'expr': write.get('expr', ''), 'groups': write.get('groups', [])}
        DataPermissionRule.objects.create(
            dimension_type='ROLE',
            dimension_value=role.role_code,
            level='ROW',
            entity=mk,
            scope_type=w_scope_type,
            scope_payload=w_payload,
            row_access='WRITE',
            actions=list(write.get('actions') or []),
            priority=0,
            status=1,
            created_by=created_by,
        )
    return build_modules_response(role)


def options_payload() -> Dict:
    """模块 × 维度矩阵 + 维度值选项（部门/用户/管理单元）。

    v2：增发 actionRegistry / presetPackages —— 动作与预设包是 **DB 可配置字典**
    （管理员可增删改），前端禁止硬编码动作清单，一律以本接口下发为准。
    """
    from . import action_registry

    dept_options = _department_options()
    user_options = _user_options()
    unit_options = _unit_options()
    modules = []
    for mk in MODULE_ORDER:
        dim_metas = []
        for d in supported_dimensions(mk):
            meta = dict(DIMENSION_META[d])
            if meta['valueType'] == 'department':
                meta['options'] = dept_options
            elif meta['valueType'] == 'user':
                meta['options'] = user_options
            elif meta['valueType'] == 'unit':
                meta['options'] = unit_options
            else:
                meta['options'] = []
            dim_metas.append(meta)
        modules.append({
            'moduleKey': mk,
            'label': MODULE_LABELS[mk],
            'dimensions': dim_metas,
            # ARCH §2.2: 数据权限向导目录走 row_filter 场景 —— 仅可下推标量
            # (filterable=True); 派生指标与不可下推字段天然排除。
            'attributeFields': attribute_fields_for(mk, scenario=SCENARIO_ROW_FILTER),
        })
    return {
        'modules': modules,
        'actionRegistry': action_registry.action_dict(),
        # 数组形态而非 {key: [...]} 映射 —— drf-camel-case 会把响应的**字典键**
        # snake→camel（owner_restricted → ownerRestricted），key 作为字典键会被
        # 破坏；作为数组元素的值则原样透传，前端拿到的 key 与存储契约一致。
        'presetPackages': [
            {'key': k, 'label': k, 'actionKeys': list(v)}
            for k, v in action_registry.preset_dict().items()
        ],
    }
