"""Request B：版本引用规则（BR-13 / AC-18）穿透测试。

验证：
- 首次标注记录当时版本；规则修改后重填已有标签 → 引用首次使用版本（不漂移）；
  全新标签 → 引用最新版本。
- 归因双写落 CandidateHistory（REASON_TAGGED）。
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db

from apps.candidate.models import Candidate, CandidateHistory
from apps.reason_library.models import ReasonTag, TagType
from apps.reason_library.services.attribution_service import (
    record_attribution,
    resolve_tag_versions,
)


@pytest.fixture
def candidate(db):
    return Candidate.objects.create(
        name='归因测试候选人', phone='13800000099', code='C90000001',
        recruit_type='social',
    )


def _tag(name: str) -> ReasonTag:
    return ReasonTag.objects.create(name=name, type=TagType.CUSTOM.value, enabled=True)


def test_first_use_records_version_then_reused_for_existing_tag(candidate, custom_rule):
    tag_a = _tag('ver-tag-a')
    tag_b = _tag('ver-tag-b')
    tag_c = _tag('ver-tag-c')

    # 首次标注：当时规则版本 = 1
    custom_rule.version = 1
    custom_rule.save(update_fields=['version'])
    rec1 = record_attribution(
        candidate, None, '淘汰', 'social', custom_rule, [tag_a.id, tag_b.id], actor=None,
    )
    assert rec1.rule_version == 1

    # 规则被修改 → 版本升到 3
    custom_rule.version = 3
    custom_rule.save(update_fields=['version'])

    # 再次标注：重填 tag_a（此前已选）→ 首次版本 1；全新 tag_c → 最新 3
    rec2 = record_attribution(
        candidate, None, '淘汰', 'social', custom_rule, [tag_a.id, tag_c.id], actor=None,
    )
    assert rec2.rule_version == 3

    v1 = {t.tag_id: t.rule_version for t in rec1.tag_records.all()}
    assert v1[tag_a.id] == 1 and v1[tag_b.id] == 1

    v2 = {t.tag_id: t.rule_version for t in rec2.tag_records.all()}
    assert v2[tag_a.id] == 1, '重填已有标签应引用首次使用版本(1)'
    assert v2[tag_c.id] == 3, '全新标签应引用最新版本(3)'

    # 直接验证解析函数
    resolved = resolve_tag_versions(candidate.id, [tag_a.id, tag_b.id, tag_c.id], 3)
    assert resolved[tag_a.id] == 1
    assert resolved[tag_b.id] == 1
    assert resolved[tag_c.id] == 3


def test_attribution_writes_candidate_history(candidate, custom_rule):
    tag = _tag('hist-tag')
    custom_rule.version = 2
    custom_rule.save(update_fields=['version'])
    record_attribution(
        candidate, None, '取消面试', 'social', custom_rule, [tag.id], note='复核', actor=None,
    )
    hist = CandidateHistory.objects.filter(candidate=candidate, action='REASON_TAGGED').last()
    assert hist is not None
    assert hist.detail['rule_version'] == 2
    assert hist.detail['tags'][0]['tag_id'] == tag.id
    assert hist.detail['tags'][0]['rule_version'] == 2
    assert hist.detail['note'] == '复核'
