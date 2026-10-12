"""数据权限模板：实例化（参数绑定）与版本漂移检测。

## 为什么是「快照」而不是「外链」

模板是**起草工具**，不是运行时真相源。若引用方在执行时实时读模板，
管理员改一次模板就会让所有在用规则**静默语义漂移** —— 这是最危险的权限缺陷
（规则界面显示的还是旧条件，实际生效的却是新条件）。

因此本模块的 instantiate() 把模板体**深拷贝 + 绑定参数**后返回，
调用方把结果快照进 scope_payload，并记 templateRef 标记（code/version/bindings）。
由此得到三条性质：

  1. 模板改版 → 在用规则语义不变，漂移由 summarize_drift() 显式报告，升级需人工确认；
  2. 模板软删 → 引用方继续按快照正常执行（不失效、不报错）；
  3. 运行时无需查模板表（零额外查询）。

## 参数占位符

语法 `${paramKey}`，只允许出现在 relation / values[].id 这两个白名单位置。
dimension / dynamicKey / kind / operator / valueSource / field 属**控制字段**，
开放占位符等于允许注入任意规则语义，因此一律拒绝。
绑定值中的字面 `${` 用反斜杠转义，替换后仍做一次「占位符全消解」断言。
"""
from __future__ import annotations

import json
import re

from .expr_compiler import validate_scope_payload

# 允许出现占位符的键名（白名单）
_PLACEHOLDER_ALLOWED_KEYS = frozenset({'relation', 'id'})
_PLACEHOLDER_RE = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}')
# 转义哨兵：必须是 **JSON 合法** 的转义序列（\u0000）。
# 早前用 \x00 字符会导致还原后 json.loads 抛 "Invalid \escape"。
_ESCAPED_SENTINEL = r'\u0000'
# JSON 文本中「反斜杠 + ${」的形态（即 Python 里的 '\\\\${'）
_ESCAPED_PREFIX = '\\\\${'

# 禁止出现占位符的控制字段
_CONTROL_KEYS = ('dimension', 'dynamicKey', 'kind', 'operator', 'valueSource', 'field')


class TemplateBindError(Exception):
    """模板绑定失败（缺参数 / 存在未绑定占位符 / 绑定后不合法）。"""


def _iter_conditions(groups):
    """逐条产出条件字典。"""
    for g in groups or []:
        if not isinstance(g, dict):
            continue
        for c in g.get('conditions') or []:
            if isinstance(c, dict):
                yield c


def _assert_placeholder_whitelist(groups) -> None:
    """占位符只允许出现在 relation / values[].id，控制字段一律拒绝。"""
    for c in _iter_conditions(groups):
        for key in _CONTROL_KEYS:
            val = c.get(key)
            if isinstance(val, str) and _PLACEHOLDER_RE.search(val):
                raise TemplateBindError(f'占位符不允许出现在控制字段「{key}」')


def unbound_placeholders(groups) -> set[str]:
    """返回模板体中尚未绑定的占位符名（供前端高亮提示）。"""
    found: set[str] = set()
    for c in _iter_conditions(groups):
        for key in (*_CONTROL_KEYS, 'relation'):
            val = c.get(key)
            if isinstance(val, str):
                found.update(_PLACEHOLDER_RE.findall(val))
        for v in (c.get('values') or []):
            if isinstance(v, dict) and isinstance(v.get('id'), str):
                found.update(_PLACEHOLDER_RE.findall(v['id']))
    return found


def instantiate(template, bindings: dict | None = None) -> dict:
    """模板 -> 实际 groups（深拷贝 + 参数替换 + 完整性断言 + 通用校验）。

    返回值可直接写入 scope_payload.groups。
    绑定结果仍需通过 validate_scope_payload —— 模板作者可能写了非法组合，
    不能因为「来自模板」就跳过校验。
    """
    bindings = bindings or {}
    params = [p for p in (template.params or []) if isinstance(p, dict)]

    # 1) 必填参数检查（有 default 的参数即使未绑定也能取到默认值，不该报错）
    for p in params:
        key = p.get('key')
        if not key:
            continue
        has_default = p.get('default') is not None
        if p.get('required') and not has_default and bindings.get(key) in (None, '', []):
            raise TemplateBindError(
                f'模板【{template.name}】缺少参数：【{p.get("label") or key}】')

    # 2) 深拷贝（不污染 template.groups，避免多次实例化互相影响）
    groups = json.loads(json.dumps(template.groups or [], ensure_ascii=False))

    # 3) 控制字段白名单检查（替换前做，此时占位符仍是原文）
    _assert_placeholder_whitelist(groups)

    # 4) 转义模板里已转义的字面 \${（还原为哨兵），随后做占位符替换
    raw = json.dumps(groups, ensure_ascii=False).replace(_ESCAPED_PREFIX, _ESCAPED_SENTINEL)

    declared = {p.get('key') for p in params if p.get('key')}
    for p in params:
        key = p.get('key')
        if not key:
            continue
        value = bindings.get(key, p.get('default'))
        if value is None:
            continue
        # json.dumps 再去掉首尾引号：既做转义又保留类型（数字不会变字符串）
        raw = raw.replace('${%s}' % key, json.dumps(value, ensure_ascii=False)[1:-1])

    # 5) 断言占位符已全消解（未声明参数的占位符也要拦住）
    rest = raw.replace(_ESCAPED_SENTINEL, '')
    leftover = _PLACEHOLDER_RE.findall(rest)
    if leftover:
        undeclared = sorted(set(leftover) - declared)
        if undeclared:
            raise TemplateBindError(f'模板存在未声明的占位符：{"、".join(undeclared)}')
        raise TemplateBindError('模板存在未绑定的占位符')

    groups = json.loads(raw.replace(_ESCAPED_SENTINEL, '${'))

    # 6) 绑定结果仍需通过通用校验
    reason = validate_scope_payload({'expr': '', 'groups': groups}, template.module_key)
    if reason:
        raise TemplateBindError(f'模板绑定后不合法：{reason}')
    return groups


def build_template_ref(template, bindings: dict | None = None) -> dict:
    """构造写入条件组的 templateRef 来源标记。"""
    return {
        'templateCode': template.code,
        'templateVersion': template.version,
        'templateName': template.name,
        'bindings': bindings or {},
    }


# ---------------------------------------------------------------------------
# 删除即失效：模板软删时给引用方打「已失效」标记
# ---------------------------------------------------------------------------
# 为什么用「标记」而不是运行时查模板是否存在：
#   运行时每查一次模板表，就等于给每次数据查询加负担（且 UserRoleV2 无 FK 反向，
#   预取不了）。而「删除模板 → 引用它的规则失效」本就是一个低频的**管理动作**，
#   把连带失效写进 scope_payload，运行时只读已有的标记，零额外查询。
#
# 为什么标记不能去掉条件本身：
#   条件本体是模板快照，删掉就等于把管理员的配置内容一并销毁。restore 后无法原样回来。
#   只打标记则可逆 —— restore() 再把标记摘掉，规则立即复活。
def apply_orphan_flag(rules, codes, *, orphaned: bool) -> int:
    """给引用了 codes 中任一模板的条件组打上/摘掉 orphaned 标记。

    rules: DataPermissionRule 的 queryset 或对象列表（只处理带 templateRef 的行级规则）。
    返回实际改动的「条件组」条数。

    幂等：标记已是目标状态时不写库（避免无谓的 UPDATE 与 updated_at 抖动）。
    """
    codes = {c for c in (codes or []) if c}
    if not codes:
        return 0

    touched_groups = 0
    touched_rules = []

    for rule in rules:
        payload = getattr(rule, 'scope_payload', None)
        if not payload or not payload.get('groups'):
            continue
        changed = False
        for g in payload['groups']:
            if not isinstance(g, dict):
                continue
            ref = g.get('templateRef')
            if not isinstance(ref, dict) or ref.get('templateCode') not in codes:
                continue
            if bool(ref.get('orphaned')) == bool(orphaned):
                continue  # 已是目标状态
            if orphaned:
                ref['orphaned'] = True
            else:
                ref.pop('orphaned', None)
            changed = True
            touched_groups += 1
        if changed:
            # 只更新 scope_payload，不碰 updated_at 之外的字段
            type(rule).objects.filter(pk=rule.pk).update(scope_payload=payload)
            touched_rules.append(rule.pk)

    return touched_groups


def drift_of(group: dict, template_lookup: dict) -> dict | None:
    """检测单个条件组的模板版本漂移，无漂移返回 None。

    template_lookup: {templateCode: template 实例}
    - 模板已软删/不存在 -> {'state': 'missing'}（引用仍按快照执行，不报错）
    - 模板版本已高于快照版本 -> {'state': 'outdated'}（需人工确认升级）
    """
    ref = group.get('templateRef')
    if not isinstance(ref, dict):
        return None
    code = ref.get('templateCode')
    tpl = template_lookup.get(code)
    # 软删记录版本号仍然相等，若不显式判 deleted_at 就会被误判成「无漂移」
    # （本函数曾经的真实 bug，由 test_template_drift_api 抓出）。
    if tpl is None or getattr(tpl, 'deleted_at', None) is not None:
        return {
            'state': 'missing',
            'templateCode': code,
            'templateName': ref.get('templateName'),
        }
    if str(getattr(tpl, 'status', '') or '').upper() == 'DISABLED':
        return {
            'state': 'disabled',
            'templateCode': code,
            'templateName': ref.get('templateName'),
        }
    snap_v = ref.get('templateVersion') or 0
    if (tpl.version or 0) > snap_v:
        return {
            'state': 'outdated',
            'templateCode': code,
            'templateName': tpl.name,
            'snapshotVersion': snap_v,
            'latestVersion': tpl.version,
        }
    return None


def summarize_drift(groups, template_lookup: dict) -> list:
    """批量检测，返回存在漂移的标记列表（供列表页提示「模板有新版本」）。

    每条标记带 groupIndex（该条件组在 groups 里的下标）—— 前端据此定位
    「要替换哪一组」，从而只改动该组，不动同模块内其它手工配置的条件组。
    """
    out = []
    for gi, g in enumerate(groups or []):
        if isinstance(g, dict):
            d = drift_of(g, template_lookup)
            if d:
                out.append(dict(d, groupIndex=gi))
    return out