"""QA 定向回归 — BUG-5 (2026-08-03 严过关, commit f970bf8)

BUG-5: 候选人 FSM 5 个 transition 缺失, service 层直接给 FSMField 赋值,
        django-fsm 抛 AttributeError, 导致 mark_onboarded/withdraw/
        mark_process_failed/pause_process/resume_process 5 个接口稳定 500。

工程师白盒测试 test_fsm_transitions.py 86 用例覆盖了模型层 + service 层。
本文件是 **HTTP 黑盒**, 独立验证:
  1. 5 个接口不再 500, 合法流转 200 + 状态变更
  2. 非法 source 返 409 (不是 silently accept, 也不是 500)
  3. 审计记录 created_by 精确指向操作人 (接 BUG-3 验过的同样原则)
  4. move_to_talent_pool 从 APPLIED 直跳人才库仍可用 (向后兼容)
  5. refresh_from_db 不再抛 AttributeError (FSMModelMixin 修复验证)
"""
import pytest

from apps.candidate.models import Candidate, CandidateHistory, CandidateState
from apps.candidate.services import CandidateService, StateTransitionError


def _mk(name='BUG5', phone='13900000001'):
    return Candidate.objects.create(name=name, phone=phone)


def _to_state(cand, *states, hr_user):
    """沿合法 FSM 路径把 cand 推到目标状态.

    注意: 每次 service 调用都在 @transaction.atomic 内部, cand.current_state 的
    Python 属性可能仍是旧值, 必须从 DB 重新查询才能拿到最新状态。
    """
    for s in states:
        if s == 'IN_PROCESS':
            CandidateService.enter_process(cand, actor=hr_user)
        elif s == 'OFFER_SENT':
            CandidateService.send_offer(cand, offer_id='OF-x', actor=hr_user)
        elif s == 'PROCESS_PAUSED':
            CandidateService.pause_process(cand, reason='r', actor=hr_user)
    cand.refresh_from_db()


def _post_transition(client, cand_id, action, **extra):
    return client.post(
        f'/api/v1/candidates/{cand_id}/transition/',
        {'action': action, **extra}, format='json',
    )


# ============================================================
# 1. 5 个接口 HTTP 200 + 状态正确落地 + 审计 created_by 正确
# ============================================================
@pytest.mark.django_db
class TestBug5HappyPathOverHttp:

    def test_mark_onboarded_offersent_to_onboarded(self, auth_hr_client, hr_user):
        cand = _mk(phone='13900011111')
        _to_state(cand, 'IN_PROCESS', 'OFFER_SENT', hr_user=hr_user)
        res = _post_transition(auth_hr_client, cand.id, 'mark_onboarded')
        assert res.status_code == 200, f'mark_onboarded 仍失败: {res.status_code} {res.content[:300]}'
        cand_db = Candidate.objects.get(pk=cand.pk)
        assert cand_db.current_state == CandidateState.ONBOARDED, cand_db.current_state
        h = CandidateHistory.objects.filter(
            candidate=cand, action='ONBOARDED',
        ).first()
        assert h is not None, 'ONBOARDED 审计缺失'
        assert h.created_by_id == hr_user.id, f'created_by 应 {hr_user.id} 实 {h.created_by_id}'

    def test_withdraw_from_in_process(self, auth_hr_client, hr_user):
        cand = _mk(phone='13900022222')
        _to_state(cand, 'IN_PROCESS', hr_user=hr_user)
        res = _post_transition(
            auth_hr_client, cand.id, 'withdraw', reason='候选人主动撤回',
        )
        assert res.status_code == 200, f'withdraw 仍失败: {res.status_code} {res.content[:300]}'
        cand_db = Candidate.objects.get(pk=cand.pk)
        assert cand_db.current_state == CandidateState.WITHDRAWN, cand_db.current_state

    def test_mark_process_failed_from_in_process(self, auth_hr_client, hr_user):
        cand = _mk(phone='13900033333')
        _to_state(cand, 'IN_PROCESS', hr_user=hr_user)
        res = _post_transition(
            auth_hr_client, cand.id, 'mark_process_failed', reason='不合适',
        )
        assert res.status_code == 200, f'fail 仍失败: {res.status_code} {res.content[:300]}'
        cand_db = Candidate.objects.get(pk=cand.pk)
        assert cand_db.current_state == CandidateState.PROCESS_FAILED, cand_db.current_state

    def test_pause_then_resume_round_trip(self, auth_hr_client, hr_user):
        cand = _mk(phone='13900044444')
        _to_state(cand, 'IN_PROCESS', hr_user=hr_user)

        res = _post_transition(auth_hr_client, cand.id, 'pause_process', reason='业务暂停')
        assert res.status_code == 200, f'pause 失败: {res.status_code} {res.content[:300]}'
        cand_db = Candidate.objects.get(pk=cand.pk)
        assert cand_db.current_state == CandidateState.PROCESS_PAUSED, cand_db.current_state

        res = _post_transition(auth_hr_client, cand.id, 'resume_process')
        assert res.status_code == 200, f'resume 失败: {res.status_code} {res.content[:300]}'
        cand_db = Candidate.objects.get(pk=cand.pk)
        assert cand_db.current_state == CandidateState.IN_PROCESS, cand_db.current_state


# ============================================================
# 2. 非法 source 必须返 409 (不是 500, 也不是 silently accept)
# ============================================================
@pytest.mark.django_db
class TestBug5InvalidSourceReturns409:

    def test_pause_from_offer_sent_returns_409(self, auth_hr_client, hr_user):
        cand = _mk(phone='13900055555')
        _to_state(cand, 'IN_PROCESS', 'OFFER_SENT', hr_user=hr_user)
        res = _post_transition(auth_hr_client, cand.id, 'pause_process', reason='x')
        assert res.status_code == 409, (
            f'非法 source 必须 409 (可见), 实际 {res.status_code} {res.content[:300]}'
        )
        cand_db = Candidate.objects.get(pk=cand.pk)
        assert cand_db.current_state == CandidateState.OFFER_SENT, (
            '非法流转不得静默修改状态, 实际被改成了 ' + cand_db.current_state
        )

    def test_resume_from_in_process_returns_409(self, auth_hr_client, hr_user):
        cand = _mk(phone='13900066666')
        _to_state(cand, 'IN_PROCESS', hr_user=hr_user)
        res = _post_transition(auth_hr_client, cand.id, 'resume_process')
        assert res.status_code == 409, (
            f'IN_PROCESS 不应能 resume, 实际 {res.status_code} {res.content[:300]}'
        )
        cand_db = Candidate.objects.get(pk=cand.pk)
        assert cand_db.current_state == CandidateState.IN_PROCESS

    def test_mark_onboarded_from_applied_returns_409(self, auth_hr_client, hr_user):
        cand = _mk(phone='13900077777')
        res = _post_transition(auth_hr_client, cand.id, 'mark_onboarded')
        assert res.status_code == 409, (
            f'APPLIED 不应能 mark_onboarded, 实际 {res.status_code} {res.content[:300]}'
        )


# ============================================================
# 3. 兼容性: move_to_talent_pool 从 APPLIED 仍可用 (BUG-5 扩大 source 后)
# ============================================================
@pytest.mark.django_db
class TestBug5BackwardCompat:
    def test_move_to_pool_from_applied(self, auth_hr_client, hr_user):
        cand = _mk(phone='13900088888')
        assert cand.current_state == CandidateState.APPLIED
        res = _post_transition(
            auth_hr_client, cand.id, 'move_to_talent_pool',
            entry_source='MANUAL', reason='业务侧直入人才库',
        )
        assert res.status_code == 200, f'直跳失败: {res.status_code} {res.content[:300]}'
        cand_db = Candidate.objects.get(pk=cand.pk)
        assert cand_db.current_state == CandidateState.TALENT_POOL


# ============================================================
# 4. FSMModelMixin 副作用: refresh_from_db 不应再炸
# ============================================================
@pytest.mark.django_db
class TestBug5FsmModelMixin:

    def test_refresh_from_db_does_not_raise(self, hr_user):
        cand = _mk(phone='13900099999')
        _to_state(cand, 'IN_PROCESS', hr_user=hr_user)
        # 模拟"QA 黑盒测试不写 FSM-aware 代码"场景: 拿 instance 后什么也不动,
        # 只调用 refresh_from_db —— 此前 protected=True 会让 DB 已存的值在
        # __dict__ 触发 AttributeError。FSMModelMixin 应当让这步正常通过。
        cand_db = Candidate.objects.get(pk=cand.pk)
        cand_db.refresh_from_db()
        assert cand_db.current_state == CandidateState.IN_PROCESS

    def test_fresh_instance_has_initial_state(self):
        cand = _mk(phone='13900010101')
        assert cand.current_state == CandidateState.APPLIED


# ============================================================
# 5. FSMModelMixin 反射元数据: 模型声明的 transition 与 PHASE2_DESIGN §12 决策表一致
# ============================================================
@pytest.mark.django_db
class TestBug5TransitionInventory:
    """防止工程师漏声明 transition (类似 BUG-5 那样) 静默通过白盒。"""

    def test_required_transitions_are_declared(self):
        from apps.candidate.models import Candidate
        declared = {
            name for name, m in vars(Candidate).items()
            if callable(m) and getattr(m, '_django_fsm', None) is not None
        }
        required = {
            'enter_process', 'send_offer', 'move_to_pool',
            'mark_onboarded', 'withdraw', 'mark_process_failed',
            'pause_process', 'resume_process',
        }
        missing = required - declared
        assert not missing, f'模型缺失 transition: {missing} —— 这正是 BUG-5 复发的迹象'

    def test_each_declared_transition_has_test_coverage(self):
        """反射元测试: 每个 transition 在测试文件里都有引用, 防止后续加 transition 但忘了写测试。"""
        import os, re
        from apps.candidate.models import Candidate
        declared = sorted({
            name for name, m in vars(Candidate).items()
            if callable(m) and getattr(m, '_django_fsm', None) is not None
        })

        test_path = os.path.join(
            os.path.dirname(__file__), '..', 'apps', 'candidate',
            'tests', 'test_fsm_transitions.py',
        )
        test_path = os.path.abspath(test_path)
        with open(test_path) as f:
            test_src = f.read()

        uncovered = []
        for name in declared:
            # 只要测试文件里有此 transition 名作为字符串, 即视为覆盖
            if not re.search(rf"\b{re.escape(name)}\b", test_src):
                uncovered.append(name)
        assert not uncovered, f'transition 缺测试覆盖: {uncovered}'