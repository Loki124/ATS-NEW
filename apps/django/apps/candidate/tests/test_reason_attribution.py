"""候选人详情页「淘汰 / 放入人才库」接入原因库场景规则测试（2026-10-19）。

覆盖：
- transition 提交 reason_tag_ids 时随主接口写入 CandidateReasonRecord + 标签明细
- 归因同时落 CandidateHistory.REASON_TAGGED（哈希链同源）
- 服务端按命中规则 max_selectable_tags 截断（前端上限仅是 UX，不作为安全边界）
- 场景无生效规则 / 标签 id 非法 → 不写归因，主流程不受影响

注意：种子数据含「预置默认规则」覆盖全部 (场景 × 招聘类型)，且
rule_scene_assignment 有 UNIQUE(scene, recruit_type) —— 测试一律复用
get_active_rule 返回的现行规则挂载自有分类/标签，不另建场景分配。
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.candidate.models import Candidate, CandidateHistory
from apps.reason_library.models import (
    CandidateReasonRecord,
    ReasonTag,
    RuleCategory,
    SceneRule,
)
from apps.reason_library.services import active_query_service as aqs

pytestmark = pytest.mark.django_db


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def api_client(hr_user):
    c = APIClient()
    c.force_authenticate(user=hr_user)
    return c


def _make_tag(name: str) -> ReasonTag:
    return ReasonTag.objects.create(name=name, type='custom', enabled=True)


def _attach_tags(rule: SceneRule, tags: list[ReasonTag]) -> None:
    """在规则下新建一个末级分类并挂载标签（不与种子数据争场景分配）。"""
    cat = RuleCategory.objects.create(rule=rule, name=_uid('测试分类'), level=1, order=999)
    for i, t in enumerate(tags):
        cat.assignments.create(tag=t, order=i)


@pytest.fixture
def a_candidate():
    """APPLIED 态候选人：FSM protected 字段只能在创建时给定初始态。"""
    return Candidate.objects.create(
        id=_uid('cf'), name='归因候选人', phone='13800002222',
        recruit_type='social', current_state='APPLIED',
    )


@pytest.fixture
def eliminate_rule():
    rule = aqs.get_active_rule('淘汰', 'social')
    if rule is None:
        pytest.skip('测试环境无「淘汰」生效规则（种子未灌入）')
    SceneRule.objects.filter(pk=rule.pk).update(max_selectable_tags=2)
    rule.refresh_from_db()
    rule._test_tag_ids = [
        _make_tag(_uid('原因-技能不匹配')).id,
        _make_tag(_uid('原因-薪资超预算')).id,
    ]
    _attach_tags(rule, list(ReasonTag.objects.filter(id__in=rule._test_tag_ids)))
    return rule


def _transition_url(c):
    return f'/api/v1/candidates/{c.id}/transition/'


class TestEliminateReasonAttribution:
    def test_transition_writes_reason_record(self, api_client, a_candidate, eliminate_rule, hr_user):
        tag_ids = eliminate_rule._test_tag_ids
        resp = api_client.post(
            _transition_url(a_candidate),
            {'action': 'mark_process_failed', 'reason': '面试未通过', 'reason_tag_ids': tag_ids},
            format='json',
        )
        assert resp.status_code == 200, resp.content
        rec = CandidateReasonRecord.objects.filter(
            candidate=a_candidate, scene='淘汰',
        ).first()
        assert rec is not None
        assert rec.rule_id == eliminate_rule.id
        assert rec.recruit_type == 'social'
        assert rec.note == '面试未通过'
        assert sorted(rec.tag_records.values_list('tag_id', flat=True)) == sorted(tag_ids)
        # 归因随审计哈希链落候选人操作历史
        assert a_candidate.histories.filter(action='REASON_TAGGED').count() == 1
        # 业务主流程不受影响：状态已流转
        a_candidate.refresh_from_db()
        assert a_candidate.current_state == 'PROCESS_FAILED'

    def test_max_selectable_truncated_server_side(self, api_client, a_candidate, eliminate_rule):
        """规则上限 2，提交 3 个合法标签 → 只落 2 个（服务端为安全边界）。"""
        tag_ids = eliminate_rule._test_tag_ids + [_make_tag(_uid('原因-超出上限')).id]
        resp = api_client.post(
            _transition_url(a_candidate),
            {'action': 'mark_process_failed', 'reason': 'x', 'reason_tag_ids': tag_ids},
            format='json',
        )
        assert resp.status_code == 200
        rec = CandidateReasonRecord.objects.get(candidate=a_candidate, scene='淘汰')
        assert rec.tag_records.count() == 2

    def test_no_active_rule_skips_attribution(self, api_client, a_candidate, monkeypatch):
        """场景无生效规则：不写归因，淘汰照常成功。"""
        monkeypatch.setattr(aqs, 'get_active_rule', lambda scene, recruit_type=None: None)
        tag = _make_tag(_uid('原因-无规则场景'))
        resp = api_client.post(
            _transition_url(a_candidate),
            {'action': 'mark_process_failed', 'reason': 'x', 'reason_tag_ids': [tag.id]},
            format='json',
        )
        assert resp.status_code == 200
        assert CandidateReasonRecord.objects.filter(candidate=a_candidate).count() == 0
        a_candidate.refresh_from_db()
        assert a_candidate.current_state == 'PROCESS_FAILED'

    def test_invalid_tag_ids_filtered(self, api_client, a_candidate, eliminate_rule):
        """悬空 id 被过滤；全部非法时不写归因。"""
        resp = api_client.post(
            _transition_url(a_candidate),
            {'action': 'mark_process_failed', 'reason': 'x', 'reason_tag_ids': ['no-such-tag']},
            format='json',
        )
        assert resp.status_code == 200
        assert CandidateReasonRecord.objects.filter(candidate=a_candidate).count() == 0
        assert a_candidate.histories.filter(action='REASON_TAGGED').count() == 0

    def test_custom_reasons_persisted(self, api_client, a_candidate, eliminate_rule):
        """末级分类 allowCustom 的自由输入随归因记录落 custom_reasons 字段。"""
        tag_ids = eliminate_rule._test_tag_ids
        custom = [
            {'category': '岗位不匹配', 'text': '候选人期望 base 在深圳'},
            {'category': '硬性条件', 'text': '英语未达到岗位要求'},
        ]
        resp = api_client.post(
            _transition_url(a_candidate),
            {
                'action': 'mark_process_failed',
                'reason': '综合评估未通过',
                'reason_tag_ids': tag_ids,
                'reason_custom_reasons': custom,
            },
            format='json',
        )
        assert resp.status_code == 200, resp.content
        rec = CandidateReasonRecord.objects.get(candidate=a_candidate, scene='淘汰')
        assert rec.custom_reasons == custom
        # 审计负载一并带出，便于追溯
        hist = a_candidate.histories.filter(action='REASON_TAGGED').first()
        assert hist is not None
        assert (hist.detail or {}).get('custom_reasons') == custom

    def test_custom_reasons_malformed_dropped(self, api_client, a_candidate, eliminate_rule):
        """无 category / 空 text 的非法项被服务端静默丢弃（不阻断主流程）。"""
        resp = api_client.post(
            _transition_url(a_candidate),
            {
                'action': 'mark_process_failed',
                'reason': 'x',
                'reason_tag_ids': eliminate_rule._test_tag_ids,
                'reason_custom_reasons': [
                    {'category': '有效分类', 'text': '有效文本'},
                    {'category': '', 'text': '缺分类'},          # 丢弃
                    {'category': '缺文本', 'text': ''},          # 丢弃
                    {'text': '缺分类字段'},                       # 丢弃
                    'not-a-dict',                                # 丢弃
                ],
            },
            format='json',
        )
        assert resp.status_code == 200
        rec = CandidateReasonRecord.objects.get(candidate=a_candidate, scene='淘汰')
        assert rec.custom_reasons == [{'category': '有效分类', 'text': '有效文本'}]


class TestTalentPoolReasonAttribution:
    def test_pool_transition_writes_reason_record(self, api_client, hr_user):
        """「放入人才库」场景：IN_PROCESS 候选人入库并落归因。"""
        rule = aqs.get_active_rule('放入人才库', 'social')
        if rule is None:
            pytest.skip('测试环境无「放入人才库」生效规则（种子未灌入）')
        tag = _make_tag(_uid('原因-岗位暂停'))
        _attach_tags(rule, [tag])
        candidate = Candidate.objects.create(
            id=_uid('cf'), name='入库候选人', phone='13800003333',
            recruit_type='social', current_state='IN_PROCESS',
        )

        resp = api_client.post(
            _transition_url(candidate),
            {
                'action': 'move_to_talent_pool',
                'reason': '岗位暂缓',
                'entry_source': 'MANUAL',
                'reason_tag_ids': [tag.id],
            },
            format='json',
        )
        assert resp.status_code == 200, resp.content
        rec = CandidateReasonRecord.objects.filter(
            candidate=candidate, scene='放入人才库',
        ).first()
        assert rec is not None
        assert rec.rule_id == rule.id
        assert list(rec.tag_records.values_list('tag_id', flat=True)) == [tag.id]
        assert candidate.histories.filter(action='REASON_TAGGED').count() == 1
        candidate.refresh_from_db()
        assert candidate.current_state == 'TALENT_POOL'
