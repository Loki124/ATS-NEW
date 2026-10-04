"""指标模板版本服务层（LIFE-1 / T02）。

唯一对 `MetricTemplateVersion` 快照表的写入口。快照表**只 INSERT**，禁止 UPDATE/DELETE；
服务层不实现任何修改/删除快照的逻辑（删除走 DB FK CASCADE，模板硬删时连带清理）。

权威数据模型：每个 `version` 号恰好对应一行 `MetricTemplateVersion`，其内容 = 该版本当时的
完整配置。0019 基线已按此写了 version=1。

设计要点（对齐文档 4.6 #2/#3）：
  - `version` 单调递增、不复用。正常编辑产生的快照版本号 = `tpl.version`（调用方已保存的新值）。
  - 回滚产生 `version+1` 的新快照（kind='rollback'，内容为回滚前状态，作审计），
    随后把目标历史版本的真实字段写回主表并将 `tpl.version += 1`；不把版本号拨回旧值。

本文件零新增依赖；不改动 models / 0019 / serializers / views / io_template。
"""
from __future__ import annotations

from typing import Optional

from apps.metrics.models import (
    AtomicMetric,
    DerivedMetric,
    MetricTemplate,
    MetricTemplateVersion,
)

# 语义字段唯一真源（D4-4a）：仅这 8 个字段变更才触发 version+1；
# status / description 不算。T03 的 views / io_template 统一从这里 import，禁止各处硬编码。
SEMANTIC_FIELDS = (
    'name',
    'atomic_metric_id',
    'derived_metric_id',
    'operators',
    'param_config',
    'value_domain',
    'param_enums',
    'param_allow_null',
)

# 回滚时从快照写回主表的「真实字段」（忽略冗余键 metric_name/metric_kind/metric_path/data_type/unit）。
_ROLLBACK_REAL_FIELDS = [
    'name',
    'atomic_metric_id',
    'derived_metric_id',
    'operators',
    'param_config',
    'value_domain',
    'param_enums',
    'param_allow_null',
    'status',
    'description',
]


class TemplateVersionError(Exception):
    """版本化操作通用异常基类。"""


class TemplateVersionNotFound(TemplateVersionError):
    """目标版本快照不存在（T03 映射 HTTP 404）。"""


class RollbackBlocked(TemplateVersionError):
    """回滚被阻止：引用指标已失效（T03 映射 HTTP 400）。绝不静默降级。"""


def build_snapshot(tpl: MetricTemplate) -> dict:
    """从模板实例拼出 15 键快照 dict（键必须与 0019 RunPython 写出的完全一致）。

    metric_name / metric_kind / metric_path / data_type / unit 来自 MetricTemplate 的 5 个
    property（冗余快照：即使将来引用指标被改/被删，历史快照仍可读出当时引用了什么）。
    其余 10 键直接取模板字段。
    """
    metric = tpl.metric  # 二选一约束保证至少一个 FK 非空，仍做防御
    return {
        'name': tpl.name,
        'atomic_metric_id': tpl.atomic_metric_id,
        'derived_metric_id': tpl.derived_metric_id,
        'metric_name': metric.name if metric is not None else None,
        'metric_kind': tpl.metric_kind,
        'metric_path': tpl.metric_path,
        'data_type': tpl.data_type,
        'unit': tpl.unit,
        'operators': tpl.operators,
        'param_config': tpl.param_config,
        'value_domain': tpl.value_domain,
        'param_enums': tpl.param_enums,
        'param_allow_null': tpl.param_allow_null,
        'status': tpl.status,
        'description': tpl.description,
    }


def diff_snapshots(old: Optional[dict], new: Optional[dict]) -> list:
    """返回在 new 中相对 old **值不同**的键名列表（只比较两 dict 共有的键）。

    用于 changed_fields。值用 `==` 比较（JSON 字段 list/dict 的相等判定即可）。
    """
    if not old or not new:
        return []
    shared = set(old) & set(new)
    return [key for key in shared if old[key] != new[key]]


def create_version_snapshot(
    tpl: MetricTemplate,
    user: object,
    note: str = '',
    kind: str = 'update',
) -> MetricTemplateVersion:
    """为「当前」tpl（字段与 version 已是调用方保存后的新值）落一条快照。

    - snapshot = 当前完整配置（build_snapshot）
    - changed_fields = diff(上一版本快照, 当前快照)；无上一版本时为 []
    - version = tpl.version（调用方保证已递增到新版本号）
    返回新建的 MetricTemplateVersion。
    """
    snapshot = build_snapshot(tpl)
    prev = MetricTemplateVersion.objects.filter(
        template=tpl, version=tpl.version - 1,
    ).first()
    changed_fields = diff_snapshots(prev.snapshot, snapshot) if prev is not None else []
    return MetricTemplateVersion.objects.create(
        template=tpl,
        version=tpl.version,
        snapshot=snapshot,
        changed_fields=changed_fields,
        change_kind=kind,
        change_note=note,
        created_by=user,
    )


def list_versions(template_id: str) -> list:
    """返回某模板的全部版本快照，按 -version 排序（最近在前）；分页交给 T04/T05。"""
    return list(
        MetricTemplateVersion.objects.filter(template_id=template_id).order_by('-version'),
    )


def rollback_template(
    tpl: MetricTemplate,
    version_no: int,
    user: object,
    note: str = '',
) -> MetricTemplate:
    """回滚模板到指定历史版本。

    步骤（严格不静默降级）：
      1. 取目标版本快照；不存在 → TemplateVersionNotFound（T03→404）。
      2. 校验快照引用的指标仍有效（status='enabled'）；任一失效 → RollbackBlocked（T03→400）。
      3. 先落一条 kind='rollback' 的审计快照（版本号 = tpl.version+1，内容为回滚前状态）。
      4. 把目标快照的 10 个真实字段写回主表，tpl.version += 1 并保存。
      5. 复用 io_template._log_template_audit 记录 ROLLBACK 审计。
    返回更新后的 tpl。
    """
    snap = MetricTemplateVersion.objects.filter(
        template=tpl, version=version_no,
    ).first()
    if snap is None:
        raise TemplateVersionNotFound(f'版本 {version_no} 的快照不存在')

    snapshot = snap.snapshot or {}
    atomic_id = snapshot.get('atomic_metric_id')
    derived_id = snapshot.get('derived_metric_id')
    if atomic_id is not None and not AtomicMetric.objects.filter(
        pk=atomic_id, status='enabled',
    ).exists():
        raise RollbackBlocked('引用的指标已不存在，无法回滚')
    if derived_id is not None and not DerivedMetric.objects.filter(
        pk=derived_id, status='enabled',
    ).exists():
        raise RollbackBlocked('引用的指标已不存在，无法回滚')

    # 3) 回滚前审计快照：记录"回滚前状态"，版本号 = tpl.version+1，kind='rollback'
    before_snapshot = build_snapshot(tpl)
    MetricTemplateVersion.objects.create(
        template=tpl,
        version=tpl.version + 1,
        snapshot=before_snapshot,
        changed_fields=diff_snapshots(before_snapshot, snapshot),
        change_kind='rollback',
        change_note=note or f'回滚到 v{version_no}',
        created_by=user,
    )

    # 4) 把历史目标版本的真实字段写回主表
    for field in _ROLLBACK_REAL_FIELDS:
        setattr(tpl, field, snapshot.get(field))
    tpl.version += 1
    tpl.save(update_fields=_ROLLBACK_REAL_FIELDS + ['version'])

    # 5) 审计（复用既有 _log_template_audit；request 缺省为 None，审计失败不阻断主流程）
    from apps.metrics.io_template import _log_template_audit
    _log_template_audit(
        user, 'ROLLBACK',
        f'模板[{tpl.name}]回滚到 v{version_no}',
        entity_id=str(tpl.id),
    )
    return tpl
