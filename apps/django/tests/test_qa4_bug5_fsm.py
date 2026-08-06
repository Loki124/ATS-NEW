"""QA-4 Round-3 黑盒 HTTP 验证：BUG-5 FSM 5 transition 修复 (commit f970bf8)。

工程师声称: mark_onboarded / withdraw / mark_process_failed / pause_process /
resume_process 这 5 个之前稳定 500 (AttributeError: Direct current_state
modification is not allowed) 的接口, 现在应:
  - 合法 source: 200 + response.currentState = 目标态 + DB 真实持久化
  - 非法 source (例如从 ONBOARDED 撤回): 409 + StateTransitionError, 不再 500

不动模型层, 纯 HTTP 黑盒打 /api/v1/candidates/{id}/transition/。
DB 验证使用 Candidate.objects.get(pk=...).current_state, 不依赖 instance 缓存,
不直接 .update() 绕过 FSM。
"""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.candidate.models import Candidate, CandidateState
from apps.candidate.services import CandidateService


@pytest.fixture
def _auth(db, super_user):
    client = APIClient()
    refresh = RefreshToken.for_user(super_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client, super_user


def _mk(name='BUG5', phone='13800000001') -> Candidate:
    return Candidate.objects.create(name=name, phone=phone)


def _post(client, cid, action, **extra):
    body = {'action': action, **extra}
    return client.post(f'/api/v1/candidates/{cid}/transition/', body, format='json')


def _db_state(cid) -> str:
    """读 DB 真实状态, 不依赖 ORM 缓存"""
    return Candidate.objects.get(pk=cid).current_state


# ============================================================
# 合法 source: 200 + response 正确 + DB 真实持久化
# ============================================================
@pytest.mark.django_db
class TestBug5LegalSourcePersists:

    def test_pause_process_persists_in_db(self, _auth):
        client, user = _auth
        c = _mk('BUG5-pause')
        CandidateService.enter_process(c, actor=user)
        assert _db_state(c.id) == CandidateState.IN_PROCESS
        r = _post(client, c.id, 'pause_process')
        assert r.status_code == 200, f'status={r.status_code} body={r.content[:200]}'
        assert r.json().get('currentState') == 'PROCESS_PAUSED'
        assert _db_state(c.id) == CandidateState.PROCESS_PAUSED, (
            'BUG: pause_process 报 200 + response.currentState=PROCESS_PAUSED, '
            f'但 DB 实际为 {_db_state(c.id)!r} —— outer transaction 把它回滚了'
        )

    def test_resume_process_persists_in_db(self, _auth):
        client, user = _auth
        c = _mk('BUG5-resume')
        CandidateService.enter_process(c, actor=user)
        CandidateService.pause_process(c, reason='setup', actor=user)
        assert _db_state(c.id) == CandidateState.PROCESS_PAUSED
        r = _post(client, c.id, 'resume_process')
        assert r.status_code == 200
        assert r.json().get('currentState') == 'IN_PROCESS'
        assert _db_state(c.id) == CandidateState.IN_PROCESS, (
            f'BUG: resume 后 DB 实际为 {_db_state(c.id)!r}'
        )

    def test_mark_onboarded_persists_in_db(self, _auth):
        client, user = _auth
        c = _mk('BUG5-onboard')
        CandidateService.enter_process(c, actor=user)
        CandidateService.send_offer(c, offer_id='OF-1', actor=user)
        assert _db_state(c.id) == CandidateState.OFFER_SENT
        r = _post(client, c.id, 'mark_onboarded', onboarding_id='OB-1')
        assert r.status_code == 200
        assert r.json().get('currentState') == 'ONBOARDED'
        assert _db_state(c.id) == CandidateState.ONBOARDED, (
            f'BUG: mark_onboarded 后 DB 实际为 {_db_state(c.id)!r}'
        )

    def test_withdraw_persists_in_db(self, _auth):
        client, user = _auth
        c = _mk('BUG5-withdraw', phone='13800000002')
        r = _post(client, c.id, 'withdraw', reason='regression test')
        assert r.status_code == 200
        assert r.json().get('currentState') == 'WITHDRAWN'
        assert _db_state(c.id) == CandidateState.WITHDRAWN, (
            f'BUG: withdraw 后 DB 实际为 {_db_state(c.id)!r}'
        )

    def test_mark_process_failed_persists_in_db(self, _auth):
        client, user = _auth
        c = _mk('BUG5-fail', phone='13800000003')
        CandidateService.enter_process(c, actor=user)
        assert _db_state(c.id) == CandidateState.IN_PROCESS
        r = _post(client, c.id, 'mark_process_failed', reason='regression')
        assert r.status_code == 200
        assert r.json().get('currentState') == 'PROCESS_FAILED'
        assert _db_state(c.id) == CandidateState.PROCESS_FAILED, (
            f'BUG: mark_process_failed 后 DB 实际为 {_db_state(c.id)!r}'
        )


# ============================================================
# 非法 source: 应 409, 不应 500
# ============================================================
@pytest.mark.django_db
class TestBug5IllegalSourceNow409:

    def test_withdraw_from_onboarded_returns_409(self, _auth):
        client, user = _auth
        c = _mk('BUG5-illegal', phone='13800000004')
        CandidateService.enter_process(c, actor=user)
        CandidateService.send_offer(c, offer_id='OF-2', actor=user)
        CandidateService.mark_onboarded(c, actor=user)
        assert _db_state(c.id) == CandidateState.ONBOARDED
        r = _post(client, c.id, 'withdraw', reason='illegal')
        assert r.status_code == 409, (
            f'非法 source 应 409, 实际 {r.status_code} {r.content[:200]} '
            f'—— 5xx 即未真正修复 FSM 校验'
        )

    def test_pause_process_from_applied_returns_409(self, _auth):
        client, user = _auth
        c = _mk('BUG5-illegal2', phone='13800000005')
        r = _post(client, c.id, 'pause_process')
        assert r.status_code == 409, (
            f'非法 source 应 409, 实际 {r.status_code} {r.content[:200]}'
        )