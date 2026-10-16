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
    dimension_label,
    hidden_dimensions_for,
    supported_dimensions,
)
from .models import DataPermissionRule
from .scope_templates import summarize_drift

# 单模块选项上限（用户量可能大，前端用虚拟滚动；此处先截取得当数量）
_USER_LIMIT = 1000
_DEPT_LIMIT = 1000
_UNIT_LIMIT = 500


def normalize_modules_payload(modules):
    """把请求体 modules 里的多词键还原成 camelCase（幂等）。

    🔴 为什么必须做（2026-10-16 兵哥「已经全部都设置了，为什么不能保存」）：
    项目 REST_FRAMEWORK 装了 `CamelCaseJSONParser`，它对**请求体**递归
    underscoreize（valueSource→value_source、dynamicKey→dynamic_key、
    templateRef→template_ref…）。而本模块全链路按 camelCase 读条件键
    （expr_compiler 的 valueSource/dynamicKey、scope_templates 的
    templateRef/templateCode、这里的 moduleKey），于是动态取值来源条件在
    到达业务逻辑前就"丢字段"了：
      - validate_scope_payload 取不到 valueSource → 掉进静态分支 →
        报「请为每条条件选择业务值」，管理员明明选了「当前登录用户」却存不进去；
      - expr_compiler 编译期同样取不到 → 即便绕过校验落库，动态条件也会
        退化成 no-op（可见范围恒为空）。

    历史测试为什么全绿：单测直接构造 camelCase dict 调用函数层，**绕过了解析器**，
    所以这条链路从来没被穿过（与 docs/ARCH_数据权限P0止血 §1.2.1 同型问题）。

    修复选点在**本模块入口**而非全局 parser：其它 API 的 snake_case 契约已按
    camelCase parser 正常工作，全局关掉会波及上百个端点；这里只把数据权限
    自己的 payload 还原成它期望的形态，且对已是 camelCase 的调用方（内部函数
    直调 / 单测）完全幂等。
    """
    from djangorestframework_camel_case.util import camelize

    if not isinstance(modules, list):
        return modules
    return camelize(modules)


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


def build_modules_response(role, normalized_modules: List[str] | None = None) -> Dict:
    """读某角色的全部模块数据权限配置 -> {roleId, roleCode, modules, writeNormalized}。

    v2：每模块返回 read 配置（mode/expr/groups，row_access=NULL 行）+ write 配置
    （write: {mode, expr, groups, actions}，row_access=WRITE 行；无 WRITE 行时
    write.mode='none' = 未配置写范围 = 沿用功能权限，前端显式展示该语义）。

    normalized_modules: 本次保存时因payload 缺 write 而被补 {mode:'none'} 的模块 key 列表。
      正常前端不会命中（payload 必带 write）；一旦命中说明前端某版本漏传，
      由调用方落审计/告警 —— 这是 P0-1 的"防复发"哨兵，见 upsert_modules。
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

    return {
        'roleId': role.id,
        'roleCode': role.role_code,
        'modules': modules,
        # P0-1 防复发哨兵：正常前端恒为 []。非空 = 有模块的 write 靠"补默认"落库，
        # 需由视图层落审计（见views_permission_v2.data_permissions）。
        'writeNormalized': sorted(normalized_modules or []),
    }


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
    modules = normalize_modules_payload(modules)
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
    """按模块**差分重建**该角色的 ROW 规则（读行 + 写行）。

    为什么不再"全删后建"（2026-10-14 P0-1 修复，设计文档 §1.2.2 改动 A）：
      全删重建把"payload 漏字段"直接等价成了"配置被抹除"——
      前端漏传 write → 写入循环里 write.mode 走 'none' 分支不重建 WRITE 行
      → 但DELETE 已经执行 → 管理员配的操作权限静默消失，而接口返回 200。
      历史上三重"看起来没问题"叠加：前端脏检查含 write、后端对 write=None
      直接放行、响应体永远回 write，于是前端察觉不到丢失。

    差分语义（对前端完全等价，但物理上更安全）：
      命中的行**原地更新**（保留 id / created_at，列表页脚注与审计不断链）；
      只删除「本次 payload 显式且非空地声明了 mode=none」的那一行；
      payload 未提及的模块、以及未表达 write 意图的模块 —— 物理上不可能被删。

    「未表达意图」与「显式取消」的区分（2026-10-14 P0-1 修复的关键，见 §0.2 D1）：
      管理员说"取消写范围"与前端没提交 write，是两件完全不同的事。
      把前者当成后者（或反过来），管理员配的操作权限都会被静默抹除——
      P0-1 的原始 complaint 根本没解决，只是顺带保住了读配置。

      未表达意图的四种形态一律**保留原 WRITE 行不动**并计入 writeNormalized：
        ① 缺 `write` 键（前端回归/ 旧客户端）
        ② `write: null`（`write: m.write` 而 m.write 为 undefined/null）
        ③ `write: {}`（中间层 JSON 深拷贝丢字段）
        ④ `write` 为非 dict（脏数据）
      只有「显式非空 dict 且 mode='none'」才算主动取消，才删行。
      详见设计文档 §1.2.2「写范围三态判定表」（v1.2 唯一口径）。

    并列铁律：
      - 读行与写行同生共死（同一个 (role, module) 的两行一起处理），
        杜绝"读行重建了、写行没重建"的错位；
      - 任一模块处理失败 → 整个事务回滚（@transaction.atomic），
        绝不出现"3 个模块存了 2 个"。

    返回最新 modules 配置 + writeNormalized（防复发哨兵，见函数末尾）。
    """
    created_by = getattr(user, 'pk', None)
    role_code = role.role_code
    # 与 validate_modules 同一道还原：解析器已把多词键 underscoreize，
    # 落库前必须转回 camelCase，否则存进去的 groups 键名与读接口/前端契约不符。
    modules = normalize_modules_payload(modules)

    # 按 entity + row_access 归组现有行：{entity: {'read': rule|None, 'write': rule|None}}
    existing: Dict[str, Dict[str, object]] = {}
    for r in DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role_code,
        level='ROW', entity__in=MODULE_ORDER,
    ):
        slot = existing.setdefault(r.entity, {'read': None, 'write': None})
        slot['write' if r.row_access == 'WRITE' else 'read'] = r

    # 本次 payload 里write 字段**显式缺失**且该模块原先有 WRITE 行的模块 key。
    # 这才是真正需要告警的情况（新建角色补默认值属正常，不记）。
    normalized: List[str] = []

    for m in modules:
        mk = m.get('module_key') or m.get('moduleKey')
        slot = existing.get(mk) or {'read': None, 'write': None}

        # ---- 读范围行（row_access=NULL，与存量语义一致）----
        mode = m.get('mode')
        scope_type = {'none': 'NONE', 'all': 'ALL', 'scope': 'CUSTOM'}[mode]
        payload = {'expr': m.get('expr', ''), 'groups': m.get('groups', [])} \
            if scope_type == 'CUSTOM' else None
        _save_rule_row(
            slot['read'], dimension_value=role_code, entity=mk,
            scope_type=scope_type, scope_payload=payload,
            row_access=None, actions=None, created_by=created_by,
        )

        # ---- 写范围行（row_access=WRITE）----
        # 判据是「**有没有表达过明确意图**」，而不是「mode 是不是 none」。
        # 无意图的四种形态 —— 缺键 / write:null / write:{} / 非 dict —— 一律
        # **保留原 WRITE 行不动**并计入 writeNormalized 哨兵；只有显式非空 dict
        # 且 mode='none' 才算管理员主动取消，才删行。
        #
        # ⚠️ 为什么不能写成 `write = m.get('write') or {}` + `w_mode = write.get('mode','none')`
        # （2026-10-14 补P0-1 变种漏洞）：那样 null/{} 会被 `or {}` 归一成 {}
        # 再取默认 'none' → 与显式 none 走同一条删除路径 → WRITE 行照样被抹除。
        # 这与P0-1 是**同一类数据丢失**（无意图的 payload 抹掉管理员配置），只是换了形态，
        # 且更难排查 —— null/{} 是 JSON 序列化的极常见产物（前端 `write: m.write` 而
        # m.write 恰为 undefined/null；或中间层 JSON.parse(JSON.stringify()) 深拷贝丢字段），
        # 发生时报错现场会显示"前端确实传了 write"，极难定位。
        #
        # 见设计文档 §1.2.2「写范围三态判定表」（v1.2 唯一口径）。
        write = m.get('write')
        if not isinstance(write, dict) or not write:
            # 未表达意图：保留原行。有历史 WRITE 行才告警 ——
            # 新建角色首轮补默认值属正常，不记（否则告警变噪声而被忽略）。
            if slot['write'] is not None:
                normalized.append(mk)
            continue

        w_mode = write.get('mode', 'none')
        if w_mode == 'none':
            # 显式且非空的 none = 管理员主动取消 → 只删本模块自己的 WRITE 行；
            # 读范围行已在上一步正常落库。
            _delete_rule_row(slot['write'])
            continue
        w_scope_type = _WRITE_MODE_TO_SCOPE[w_mode]
        w_payload = {'expr': write.get('expr', ''), 'groups': write.get('groups', [])} \
            if w_scope_type == 'CUSTOM' else None
        _save_rule_row(
            slot['write'], dimension_value=role_code, entity=mk,
            scope_type=w_scope_type, scope_payload=w_payload, row_access='WRITE',
            actions=list(write.get('actions') or []), created_by=created_by,
        )

    # ---- 未被本次 payload 提及的模块：不动（差分的核心）----
    # 说明：前端永远提交全部 5 个模块（useRoleDataPerm.load() 用 MODULE_KEYS 补齐），
    # 保留"不删"分支是为了将来支持按模块局部保存时不误删。
    return build_modules_response(role, normalized)


def _save_rule_row(rule, *, dimension_value, entity, scope_type, scope_payload,
                   row_access, actions, created_by) -> None:
    """原地更新已有规则行或新建一行（差分重建的写侧原子操作）。

    原地更新保留 id / created_at —— 列表页脚注、审计链、外部引用都不断链
    （这正是"全删后建"被弃用的另一半原因：它每次保存都换一批 id）。
    """
    if rule is None:
        DataPermissionRule.objects.create(
            dimension_type='ROLE',
            dimension_value=dimension_value,
            level='ROW',
            entity=entity,
            scope_type=scope_type,
            scope_payload=scope_payload,
            row_access=row_access,
            actions=actions,
            status=1,
            created_by=created_by,
        )
        return
    rule.scope_type = scope_type
    rule.scope_payload = scope_payload
    rule.row_access = row_access
    rule.actions = actions
    rule.status = 1
    # updated_at 必须显式列出：TimestampedModel.updated_at 是 auto_now=True
    # （apps/common/models.py:17），不在 update_fields 里就不会被写。
    rule.save(update_fields=[
        'scope_type', 'scope_payload', 'row_access', 'actions', 'status', 'updated_at',
    ])


def _delete_rule_row(rule) -> None:
    """删除一行规则（None 时无操作）—— 差分重建里唯一允许的删除路径。"""
    if rule is not None:
        rule.delete()


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
            # 🔴 2026-10-15 兵哥拍板：去掉「管理单元」维度。
            # 仅在此处**不下发** —— 后端 field_map / expr_compiler / context_resolvers
            # 的 unit 映射与 iter_unit_scopes 展开逻辑**一行不动**，故存量规则里
            # 已用 unit 的条件仍能正常回显（前端按 DIMENSION_META 兜底出文案）并照常执行。
            # 禁前端过滤：前端拿到的是全量维度列表，隐藏逻辑散落两处反而更易漏。
            if d in hidden_dimensions_for(mk):
                continue
            meta = dict(DIMENSION_META[d])
            # 模块化文案优先（需求部门/需求负责人/需求创建人），缺省回落通用名。
            # 理由：同一个「部门」在不同模块指向不同实体 —— candidate 的 dept 其实是
            # referrer__department_id（推荐人部门），照叫「部门」会误导。
            meta['label'] = dimension_label(mk, d)
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
            {
                'key': k,
                'label': v.get('label') or k,
                'actionKeys': list(v.get('action_keys') or []),
                'module': v.get('module'),
            }
            for k, v in action_registry.preset_dict().items()
        ],
    }
