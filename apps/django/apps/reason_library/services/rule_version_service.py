"""场景规则版本服务层 (T-B / T-C)。

唯一对 `SceneRuleVersion` 快照表的写入口。快照表**只 INSERT**，禁止 UPDATE/DELETE；
服务层不实现任何修改/删除快照的逻辑（删除走 DB FK CASCADE，规则硬删时连带清理）。

设计要点（对齐 metrics app 的 template_version 服务）:
  - `version` 单调递增、不复用。正常编辑产生的快照版本号 = `rule.version`（调用方保存后的新值）。
  - 回滚产生 `version+1` 的新快照（kind='rollback'，内容为回滚后的目标状态），
    随后把目标历史版本的真实字段经 WizardService 写回主表并将 `rule.version += 1`；
    不把版本号拨回旧值。
  - snapshot 统一为 WizardService 消费的 snake_case 载荷形状，回滚可直接喂回 WizardService.save，
    复用既有原子保存路径（含场景冲突校验、分类树 diff、标签绑定 diff）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..models import SceneRule, SceneRuleVersion


def build_snapshot(rule: SceneRule) -> Dict[str, Any]:
    """从规则实例拼出 WizardService 消费的 snake_case 载荷 dict（回滚可直接喂回 save）。

    字段:
      - 头部标量: name / description / enabled / max_selectable_tags / modal_title
      - categories: [{id, name, order, allow_custom, level, color, parent_id, tag_ids}]
      - scene_assignments: [{scene, recruit_type}]
    """
    categories = [
        {
            'id': c.id,
            'name': c.name,
            'order': c.order,
            'allow_custom': c.allow_custom,
            'level': c.level,
            'color': c.color or '',
            'parent_id': c.parent_id,
            'tag_ids': list(c.assignments.values_list('tag_id', flat=True)),
        }
        for c in rule.categories.all().order_by('level', 'order', 'id')
    ]
    scene_assignments = [
        {'scene': a.scene, 'recruit_type': a.recruit_type}
        for a in rule.scene_assignments.all()
    ]
    return {
        'name': rule.name,
        'description': rule.description,
        'enabled': rule.enabled,
        'max_selectable_tags': rule.max_selectable_tags,
        'modal_title': rule.modal_title,
        'categories': categories,
        'scene_assignments': scene_assignments,
    }


def diff_snapshots(old: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> List[str]:
    """返回在 new 中相对 old **值不同**的键名列表（只比较两 dict 共有的顶层键）。

    嵌套列表（categories/scene_assignments）用 `==` 比较（结构相同即相等）。
    """
    if not old or not new:
        return []
    shared = set(old) & set(new)
    return [key for key in shared if old[key] != new[key]]


def create_version_snapshot(
    rule: SceneRule,
    user: object,
    kind: str = 'update',
    note: str = '',
) -> SceneRuleVersion:
    """为「当前」rule（字段与 version 已是调用方保存后的新值）落一条快照。

    - snapshot = 当前完整配置（build_snapshot）
    - changed_fields = diff(上一版本快照, 当前快照)；无上一版本时为 []
    - version = rule.version（调用方保证已递增到新版本号）
    返回新建的 SceneRuleVersion。
    """
    snapshot = build_snapshot(rule)
    prev = SceneRuleVersion.objects.filter(
        rule=rule, version=rule.version - 1,
    ).first()
    changed_fields = diff_snapshots(prev.snapshot, snapshot) if prev is not None else []
    # get_or_create 而非 create：消除并发更新撞 uniq_scenerule_version 唯一约束导致的
    # IntegrityError → 500。两名 HR 同时编辑同一规则时都读到旧 version 并算出相同新
    # version，第二个 create 会撞约束；get_or_create 在 create 失败时自动回退到 get，
    # 复用已存在的快照（二者内容一致），不抛 500。
    obj, _created = SceneRuleVersion.objects.get_or_create(
        rule=rule,
        version=rule.version,
        defaults={
            'snapshot': snapshot,
            'changed_fields': changed_fields,
            'change_kind': kind,
            'change_note': note,
            'created_by': user,
        },
    )
    return obj


def list_versions(rule_id: str) -> List[SceneRuleVersion]:
    """返回某规则的全部版本快照，按 -version 排序（最近在前）。"""
    return list(
        SceneRuleVersion.objects.filter(rule_id=rule_id).order_by('-version'),
    )


def rollback_rule(
    rule: SceneRule,
    version_no: int,
    user: object,
    note: str = '',
) -> SceneRule:
    """回滚规则到指定历史版本。

    步骤（严格不静默降级）:
      1. 取目标版本快照；不存在 → 抛 SceneRuleVersionNotFound（view → 404）。
      2. 把目标快照的载荷经 WizardService.save 写回主表（复用原子保存路径,
         含场景冲突校验 / 分类树 diff / 标签绑定 diff）；save 内部会将 rule.version += 1。
      3. 落一条 kind='rollback' 的快照（版本号 = 写回后的 rule.version），内容为回滚后状态。
    返回写回后的 rule。
    """
    from .wizard_service import WizardService

    snap = SceneRuleVersion.objects.filter(
        rule=rule, version=version_no,
    ).first()
    if snap is None:
        raise SceneRuleVersionNotFound(f'版本 {version_no} 的快照不存在')

    payload = snap.snapshot or {}
    service = WizardService()
    # 事务已在 wizard_service.save 内；这里直接调用，写回成功即代表语义成立。
    updated_rule = service.save(
        rule_id=rule.id,
        payload=payload,
        user=user,
    )
    create_version_snapshot(
        updated_rule,
        user,
        kind='rollback',
        note=note or f'回滚到 v{version_no}',
    )
    return updated_rule


class SceneRuleVersionError(Exception):
    """版本化操作通用异常基类。"""


class SceneRuleVersionNotFound(SceneRuleVersionError):
    """目标版本快照不存在（view 映射 HTTP 404）。"""
