"""归因数据回写服务（Request B：版本引用规则，对应 BR-13 / AC-18）。

设计要点：
- ``record_attribution``：六业务节点提交原因标注时调用，**随业务主接口一并提交，不单独建接口**。
  双写 ``candidate_reason_record`` + ``candidate_reason_record_tag``，并落
  ``CandidateHistory``（action=REASON_TAGGED，与现有审计哈希链同源）。
- ``resolve_tag_versions``：实现「首次使用版本引用」——
  某标签在本候选人此前已有归因记录 → 引用其**首次归因时记录的版本**（最早一条），
  不随规则后续修改而漂移；全新标签 → 引用最新版本（reason_rule_version）。
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from nanoid import generate as nanoid_generate

from apps.reason_library.models import (
    CandidateReasonRecord,
    CandidateReasonRecordTag,
)


def _actor_id(actor):
    return getattr(actor, 'id', None) if (actor and getattr(actor, 'is_authenticated', False)) else None


def resolve_tag_versions(candidate_id: str, tag_ids: Iterable[str], latest_rule_version: int) -> Dict[str, int]:
    """解析每个标签应引用的规则版本。

    规则（BR-13）：
    - 标签在本候选人此前已有归因记录 → 引用首次归因时记录的版本（最早一条
      ``candidate_reason_record_tag.rule_version``），不随规则后续修改而漂移。
    - 标签在本候选人无历史归因记录（全新标签）→ 引用 latest_rule_version（当前最新版本）。
    """
    tag_ids = list(tag_ids)
    first_version: Dict[str, int] = {}
    if tag_ids:
        existing = (
            CandidateReasonRecordTag.objects
            .filter(record__candidate_id=candidate_id, tag_id__in=tag_ids)
            .select_related('record')
            .order_by('record__created_at', 'record_id', 'id')
        )
        for row in existing:
            if row.tag_id not in first_version:
                first_version[row.tag_id] = row.rule_version
    return {tag_id: first_version.get(tag_id, latest_rule_version) for tag_id in tag_ids}


def record_attribution(candidate, application, scene: str, recruit_type: str,
                       rule, tag_ids: List[str], note: str = '',
                       custom_reasons: Optional[List[Dict]] = None, actor=None) -> CandidateReasonRecord:
    """双写归因记录 + 候选人审计（不单独建接口，由六业务端点主接口调用）。

    custom_reasons: 末级分类 allowCustom 时终端用户输入的自由文本，
      形如 [{"category": "岗位不匹配", "text": "..."}]；空/非法项在服务端静默丢弃。
    返回创建的 ``CandidateReasonRecord``。
    """
    latest_version = getattr(rule, 'version', 1)
    versions = resolve_tag_versions(candidate.id, tag_ids, latest_version)

    # 仅保留 {category: 非空 str, text: 非空 str} 的合法项（best-effort，不阻断主流程）
    clean_custom: List[Dict] = []
    for item in (custom_reasons or []):
        if isinstance(item, dict) and item.get('category') and item.get('text'):
            clean_custom.append({'category': str(item['category']), 'text': str(item['text'])})

    record = CandidateReasonRecord.objects.create(
        candidate=candidate,
        application=application,
        scene=scene,
        recruit_type=recruit_type,
        rule=rule,
        rule_version=latest_version,
        note=note,
        custom_reasons=clean_custom,
        created_by=actor if _actor_id(actor) else None,
    )
    tag_rows = [
        CandidateReasonRecordTag(
            id=nanoid_generate(size=21),
            record=record, tag_id=tag_id, rule_version=version,
        )
        for tag_id, version in versions.items()
    ]
    CandidateReasonRecordTag.objects.bulk_create(tag_rows)

    # 审计：候选人维度操作历史（哈希链同源，不可篡改）
    from apps.candidate.audit import record_reason_tagged
    record_reason_tagged(candidate, {
        'scene': scene,
        'recruit_type': recruit_type,
        'rule_id': rule.id,
        'rule_version': latest_version,
        'tags': [{'tag_id': tag_id, 'rule_version': version} for tag_id, version in versions.items()],
        'note': note,
        'custom_reasons': clean_custom,
    }, actor)

    return record
