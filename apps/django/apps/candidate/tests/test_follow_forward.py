"""候选人详情页「关注 / 转发」端点测试（2026-10-19 新增）。

覆盖：
- follow: GET 回显 / POST 关注（幂等）/ DELETE 取消关注
- forward: POST 写记录 + 审计 / GET 列记录 / 自我转发与不存在用户被拒
- 两条动作都进 CandidateHistory 哈希链（可溯源）

权限口径：
- 关注是**个人偏好**，不经过 ensure_operable（不改简历业务状态）；
- 转发是简历操作动作，走 ensure_writable(action='recommend') + ensure_operable，
  与「推荐其他职位」同口径。
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.candidate.models import Candidate, CandidateFollow, CandidateForward, CandidateHistory

pytestmark = pytest.mark.django_db


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = 'u'):
    return get_user_model().objects.create_user(
        username=_uid(tag), password='Test@1234',
    )


@pytest.fixture
def api_client(hr_user):
    c = APIClient()
    c.force_authenticate(user=hr_user)
    return c


@pytest.fixture
def a_candidate():
    return Candidate.objects.create(
        id=_uid('cf'), name='关注候选人', phone='13800001234', recruit_type='social',
    )


def _follow_url(c):
    return f'/api/v1/candidates/{c.id}/follow/'


def _forward_url(c):
    return f'/api/v1/candidates/{c.id}/forward/'


class TestCandidateFollow:
    def test_get_follow_state_defaults_false(self, api_client, a_candidate):
        resp = api_client.get(_follow_url(a_candidate))
        assert resp.status_code == 200
        assert resp.json()['data']['isFollowed'] is False

    def test_post_follow_is_idempotent(self, api_client, a_candidate, hr_user):
        r1 = api_client.post(_follow_url(a_candidate), {}, format='json')
        assert r1.status_code == 200
        r2 = api_client.post(_follow_url(a_candidate), {}, format='json')
        assert r2.status_code == 200
        # 复合唯一约束保证只有一条记录
        assert CandidateFollow.objects.filter(candidate=a_candidate, user=hr_user).count() == 1
        assert api_client.get(_follow_url(a_candidate)).json()['data']['isFollowed'] is True

    def test_follow_writes_audit_history(self, api_client, a_candidate):
        api_client.post(_follow_url(a_candidate), {}, format='json')
        assert a_candidate.histories.filter(action='FOLLOWED').count() == 1

    def test_delete_unfollow(self, api_client, a_candidate, hr_user):
        api_client.post(_follow_url(a_candidate), {}, format='json')
        resp = api_client.delete(_follow_url(a_candidate))
        assert resp.status_code == 200
        assert CandidateFollow.objects.filter(candidate=a_candidate, user=hr_user).count() == 0
        assert a_candidate.histories.filter(action='UNFOLLOWED').count() == 1

    def test_follow_is_personal_scoped(self, api_client, a_candidate, hr_user, hrbp_user):
        """关注仅本人可见：另一位有权限的同事调 GET 应为 False（不共享关注状态）。"""
        api_client.post(_follow_url(a_candidate), {}, format='json')
        c2 = APIClient()
        c2.force_authenticate(user=hrbp_user)
        resp = c2.get(_follow_url(a_candidate))
        assert resp.status_code == 200
        assert resp.json()['data']['isFollowed'] is False

    def test_follow_requires_candidate_read_permission(self, api_client, a_candidate):
        """无任何角色的用户访问候选人详情应被拒（403），不应泄露关注状态。"""
        outsider = _user('outsider')
        c2 = APIClient()
        c2.force_authenticate(user=outsider)
        assert c2.get(_follow_url(a_candidate)).status_code == 403


class TestCandidateForward:
    def test_forward_creates_record(self, api_client, a_candidate, hr_user):
        target = _user('peer')
        resp = api_client.post(
            _forward_url(a_candidate),
            {'to_user_ids': [str(target.id)], 'note': '这位候选人很合适'},
            format='json',
        )
        assert resp.status_code == 200
        row = CandidateForward.objects.get(candidate=a_candidate, to_user=target)
        assert row.from_user == hr_user
        assert row.note == '这位候选人很合适'

    def test_forward_writes_audit_history(self, api_client, a_candidate):
        target = _user('peer')
        api_client.post(
            _forward_url(a_candidate), {'to_user_ids': [str(target.id)]}, format='json',
        )
        h = a_candidate.histories.filter(action='FORWARDED').first()
        assert h is not None
        assert h.detail['to']['id'] == str(target.id)
        # 审计行进哈希链，可被完整性校验覆盖
        assert h.row_hash and h.seq >= 1

    def test_forward_to_multiple_users(self, api_client, a_candidate):
        t1, t2 = _user('p1'), _user('p2')
        resp = api_client.post(
            _forward_url(a_candidate),
            {'to_user_ids': [str(t1.id), str(t2.id)]},
            format='json',
        )
        assert resp.status_code == 200
        assert CandidateForward.objects.filter(candidate=a_candidate).count() == 2

    def test_forward_to_self_rejected(self, api_client, a_candidate, hr_user):
        resp = api_client.post(
            _forward_url(a_candidate), {'to_user_ids': [str(hr_user.id)]}, format='json',
        )
        assert resp.status_code == 200
        result = resp.json()['data']['results'][0]
        assert result['success'] is False
        assert result['error'] == 'FORBIDDEN_SELF'
        assert CandidateForward.objects.filter(candidate=a_candidate).count() == 0

    def test_forward_unknown_user_rejected(self, api_client, a_candidate):
        """合法类型但不存在的用户 id → 该条 USER_NOT_FOUND，不影响其它人。"""
        target = _user('peer')
        resp = api_client.post(
            _forward_url(a_candidate),
            {'to_user_ids': [str(target.id), '99999']},
            format='json',
        )
        assert resp.status_code == 200
        results = resp.json()['data']['results']
        by_id = {r['toUserId']: r for r in results}
        assert by_id[str(target.id)]['success'] is True
        assert by_id['99999']['error'] == 'USER_NOT_FOUND'
        assert CandidateForward.objects.filter(candidate=a_candidate).count() == 1

    def test_forward_malformed_id_returns_400(self, api_client, a_candidate):
        """非数字 id 打到整型主键上属请求错误 → 400，绝不能 500。"""
        resp = api_client.post(
            _forward_url(a_candidate), {'to_user_ids': ['abc']}, format='json',
        )
        assert resp.status_code == 400
        assert CandidateForward.objects.filter(candidate=a_candidate).count() == 0

    def test_forward_empty_targets_400(self, api_client, a_candidate):
        resp = api_client.post(_forward_url(a_candidate), {'to_user_ids': []}, format='json')
        assert resp.status_code == 400

    def test_get_forward_list(self, api_client, a_candidate):
        target = _user('peer')
        api_client.post(
            _forward_url(a_candidate),
            {'to_user_ids': [str(target.id)], 'note': '速看'},
            format='json',
        )
        resp = api_client.get(_forward_url(a_candidate))
        assert resp.status_code == 200
        rows = resp.json()['data']['results']
        assert len(rows) == 1
        assert rows[0]['note'] == '速看'


class TestAuditImmutability:
    def test_history_hash_chain_covers_new_actions(self, api_client, a_candidate):
        """关注与转发产生的审计行应串成完整哈希链（prev_hash 首尾相接）。"""
        target = _user('peer')
        api_client.post(_forward_url(a_candidate), {'to_user_ids': [str(target.id)]}, format='json')
        api_client.post(_follow_url(a_candidate), {}, format='json')

        rows = list(a_candidate.histories.order_by('seq'))
        assert len(rows) >= 2
        prev = ''
        for r in rows:
            assert r.prev_hash == prev
            assert r.row_hash
            prev = r.row_hash

        # 不可篡改：既有审计行禁止 UPDATE
        from apps.candidate.audit import AuditImmutabilityError
        row = rows[0]
        row.action = 'TAMPERED'
        with pytest.raises(AuditImmutabilityError):
            row.save()
