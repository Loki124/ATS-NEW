"""QA 定向回归 — BUG-3 / BUG-4 (2026-08-03 严过关, commit 1e1ed1e)

BUG-3: CandidateHistory 无 operator 字段, services.py 12 处 operator=actor
        导致候选人主写链路全部 500 (TypeError)。
BUG-4: id_card_no 是 blank=True/null=False 的加密列, 未填身份证时传 None
        导致 IntegrityError(NOT NULL)。

本文件的设计原则 —— **不只看 HTTP 状态码, 必须查库确认审计记录真实落地**:
  HTTP 200 只能证明"没炸", 不能证明"审计历史写进去了、created_by 指对了人"。
  BUG-3 的本质是审计写入失败, 所以每条链路都要断言:
    1. 接口不再 500
    2. CandidateHistory 记录数 +1
    3. 该记录 action 正确
    4. 该记录 created_by 精确指向操作人 (不是 None、不是别人)
"""
import pytest

from apps.candidate.models import Candidate, CandidateHistory
from apps.candidate.services import CandidateService, StateTransitionError

VALID_ID_CARD = '11010119900101987X'


def _mk(name='回归候选人', phone='13900001111', **kw) -> Candidate:
    return Candidate.objects.create(name=name, phone=phone, **kw)


def _last_history(cand):
    return CandidateHistory.objects.filter(candidate=cand).order_by('-created_at').first()


def _assert_audit(cand, action, actor, before_count):
    """审计三连: 目标 action 记录存在 / 总数增加 / created_by 精确指向操作人.

    注意: 不能断言"恰好 +1"。apps/candidate/signals.py 的 post_save 钩子在状态
    变化时会**额外**写一条 STATE_CHANGED, 所以一次 enter_process 实际产生 2 条
    (service 的 ENTER_PROCESS + signal 的 STATE_CHANGED)。这是既有设计, 不是 bug,
    我第一版断言 +1 是测试侧写错了。这里改为精确定位 service 写的那一条。
    """
    after = CandidateHistory.objects.filter(candidate=cand).count()
    assert after > before_count, (
        f'{action}: 审计记录完全未写入 (before={before_count}, after={after}) '
        f'—— BUG-3 的本质就是这条历史丢了, HTTP 200 也不代表它写进去了'
    )
    h = CandidateHistory.objects.filter(candidate=cand, action=action).first()
    assert h is not None, (
        f'总记录数涨了但找不到 action={action} 的那条 —— '
        f'实际有: {list(CandidateHistory.objects.filter(candidate=cand).values_list("action", flat=True))}'
    )
    assert h.created_by_id == actor.id, (
        f'{action}: created_by 应指向操作人 {actor.id}, 实际 {h.created_by_id} '
        f'—— 审计溯源断链'
    )
    return h


# ============================================================
# BUG-3 — HTTP 黑盒: 主写链路不再 500 且审计真实落库
# ============================================================
@pytest.mark.django_db
class TestBug3WriteChainsOverHttp:

    def test_create_writes_audit_with_created_by(self, auth_hr_client, hr_user):
        res = auth_hr_client.post('/api/v1/candidates/', {
            'name': 'BUG3建档', 'phone': '13900002222',
            'email': 'bug3@example.com', 'id_card_no': VALID_ID_CARD,
        }, format='json')
        assert res.status_code in (200, 201), f'建档仍失败: {res.status_code} {res.content[:400]}'

        cand = Candidate.objects.get(name='BUG3建档')
        h = CandidateHistory.objects.filter(candidate=cand, action='CREATED').first()
        assert h is not None, '建档成功但 CREATED 审计记录缺失'
        assert h.created_by_id == hr_user.id, (
            f'CREATED.created_by 应为 {hr_user.id}, 实际 {h.created_by_id}'
        )

    def test_enter_process_over_http(self, auth_hr_client, hr_user):
        cand = _mk(name='BUG3进流程')
        before = CandidateHistory.objects.filter(candidate=cand).count()
        res = auth_hr_client.post(
            f'/api/v1/candidates/{cand.id}/transition/',
            {'action': 'enter_process'}, format='json',
        )
        assert res.status_code == 200, f'enter_process 仍失败: {res.status_code} {res.content[:400]}'
        _assert_audit(cand, 'ENTER_PROCESS', hr_user, before)

    def test_send_offer_over_http(self, auth_hr_client, hr_user):
        cand = _mk(name='BUG3发offer')
        CandidateService.enter_process(cand, actor=hr_user)
        cand.refresh_from_db()
        before = CandidateHistory.objects.filter(candidate=cand).count()
        res = auth_hr_client.post(
            f'/api/v1/candidates/{cand.id}/transition/',
            {'action': 'send_offer', 'offer_id': 'OF-1'}, format='json',
        )
        assert res.status_code == 200, f'send_offer 仍失败: {res.status_code} {res.content[:400]}'
        _assert_audit(cand, 'OFFER_SENT', hr_user, before)

    def test_merge_over_http(self, auth_hr_client, hr_user):
        primary = _mk(name='BUG3主', phone='13900003333')
        dup = _mk(name='BUG3副', phone='13900004444')
        before = CandidateHistory.objects.filter(candidate=primary).count()
        res = auth_hr_client.post('/api/v1/candidates/merge/', {
            'primary_id': primary.id, 'duplicate_ids': [dup.id],
        }, format='json')
        assert res.status_code in (200, 201), f'merge 仍失败: {res.status_code} {res.content[:400]}'
        after = CandidateHistory.objects.filter(candidate=primary).count()
        assert after > before, 'merge 成功但审计记录未写入'
        h = _last_history(primary)
        assert h.created_by_id == hr_user.id, f'merge 审计 created_by 错误: {h.created_by_id}'


# ============================================================
# BUG-3 — 服务层直调: 覆盖 HTTP 层被 FSM 挡住的链路
# ============================================================
@pytest.mark.django_db
class TestBug3ServiceLayer:

    def test_move_to_talent_pool_writes_audit(self, hr_user):
        cand = _mk(name='BUG3人才库')
        before = CandidateHistory.objects.filter(candidate=cand).count()
        CandidateService.move_to_talent_pool(
            cand, entry_source='MANUAL', reason='回归', actor=hr_user,
        )
        _assert_audit(cand, 'TO_TALENT_POOL', hr_user, before)

    def test_signal_audit_records_lose_operator_identity(self, hr_user):
        """BUG-6 修复后正向断言: 两条契约必须同时成立。

        1. service 显式记录的场景: STATE_CHANGED.created_by 应等于 actor
           (因为每个 service 转换方法在 save() 前调用 _record_state_change)
        2. signal 兜底的场景: 旁路 .update() 触发的 post_save,
           signal 应补一条 STATE_CHANGED 但 created_by=None (NULL 表示
           "非业务路径自动审计, 不可溯源" 是合法值)
        """
        # 路径 1: service 显式
        cand = _mk(name='BUG6-service-路径')
        CandidateService.enter_process(cand, actor=hr_user)
        sc = CandidateHistory.objects.filter(
            candidate=cand, action='STATE_CHANGED',
        ).first()
        assert sc is not None, 'service 路径应写 STATE_CHANGED'
        assert sc.created_by_id == hr_user.id, (
            f'service 显式场景 created_by 必须是 actor={hr_user.id}, '
            f'实际 {sc.created_by_id}'
        )
        assert sc.detail.get('from_state') == 'APPLIED'
        assert sc.detail.get('to_state') == 'IN_PROCESS'

        # 路径 2: signal 兜底 (旁路 service 直接 .save(), 走 post_save 但不预置标志)
        # 真实兜底场景: Django admin / .save(update_fields=...) / 测试直连模型 /
        # 任何不经 service 直接改动 current_state 的路径。django-fsm 的 protected=True
        # 会阻止常规属性赋值, 这里用 __dict__ 绕过(模拟 ORM/测试直改 DB 后又 save)。
        cand2 = _mk(name='BUG6-signal-兜底')
        cand2.__dict__['current_state'] = 'OFFER_SENT'  # 绕过 FSMField 描述符
        cand2.save()  # 触发 post_save, signal 看到 _state_change_recorded 未置位, 兜底写一行
        sc2 = CandidateHistory.objects.filter(
            candidate=cand2, action='STATE_CHANGED',
        ).order_by('-created_at').first()
        assert sc2 is not None, 'signal 兜底路径应写 STATE_CHANGED'
        assert sc2.created_by_id is None, (
            f'signal 兜底场景 created_by 应为 NULL, 实际 {sc2.created_by_id}'
        )
        # 兜底写入的 detail 用 {from, to} 而非 {from_state, to_state}
        # (signal 是退化兜底, 与 service 显式格式不同, 故意保留以便排查)

    def test_operator_kwarg_is_truly_gone(self):
        """反证: 直接用 operator= 仍应抛 TypeError, 说明字段确实不存在,
        修复方式是改调用方而不是给模型硬加字段(那会掩盖问题)。"""
        cand = _mk(name='BUG3反证')
        with pytest.raises(TypeError, match='operator'):
            CandidateHistory.objects.create(
                candidate=cand, action='X', detail={}, operator=None,
            )


# ============================================================
# BUG-4 — 不填身份证建档 (最常见路径)
# ============================================================
@pytest.mark.django_db
class TestBug4IdCardNone:

    def test_create_without_id_card_over_http(self, auth_hr_client):
        """BUG-4 主场景: id_card_no 完全不传。"""
        res = auth_hr_client.post('/api/v1/candidates/', {
            'name': 'BUG4无身份证', 'phone': '13900005555',
        }, format='json')
        assert res.status_code in (200, 201), (
            f'不填身份证建档失败: {res.status_code} {res.content[:400]}'
        )
        cand = Candidate.objects.get(name='BUG4无身份证')
        assert cand.id_card_no == '', f'应落空串, 实际 {cand.id_card_no!r}'

    def test_create_with_empty_string_id_card(self, auth_hr_client):
        res = auth_hr_client.post('/api/v1/candidates/', {
            'name': 'BUG4空串', 'phone': '13900006666', 'id_card_no': '',
        }, format='json')
        assert res.status_code in (200, 201), (
            f'空串身份证建档失败: {res.status_code} {res.content[:400]}'
        )

    def test_id_card_hash_empty_when_no_id_card(self, auth_hr_client):
        """回归 BUG-1: 无身份证时 hash 必须是空串, 不能是 hash('') —— 
        否则所有无身份证候选人会互相误判为重复。"""
        auth_hr_client.post('/api/v1/candidates/', {
            'name': 'BUG4hash1', 'phone': '13900007777',
        }, format='json')
        auth_hr_client.post('/api/v1/candidates/', {
            'name': 'BUG4hash2', 'phone': '13900008888',
        }, format='json')
        c1 = Candidate.objects.get(name='BUG4hash1')
        c2 = Candidate.objects.get(name='BUG4hash2')
        assert c1.id_card_hash == '', f'无身份证不应有 hash, 实际 {c1.id_card_hash!r}'
        assert c2.id_card_hash == ''


# ============================================================
# BUG-5 — 工程师自曝未修, QA 独立复验其真实性与影响面
# ============================================================
@pytest.mark.django_db
class TestBug5FsmDirectAssignment:
    """工程师在 1e1ed1e 的 commit message 里自曝 5 处 FSMField 直接赋值未修。
    QA 不能只采信 commit message —— 这里独立实证到底哪些接口还在 500。"""

    def _to_offer_sent(self, hr_user):
        cand = _mk(name=f'BUG5-{id(self)}', phone='13900009999')
        CandidateService.enter_process(cand, actor=hr_user)
        CandidateService.send_offer(cand, offer_id='OF-9', actor=hr_user)
        cand.refresh_from_db()
        return cand

    def test_mark_onboarded_still_broken(self, hr_user):
        cand = self._to_offer_sent(hr_user)
        try:
            CandidateService.mark_onboarded(cand, actor=hr_user)
        except (AttributeError, StateTransitionError) as e:
            pytest.xfail(f'BUG-5 未修 (工程师已上报, 待 FSM 设计决策): {e}')
        cand.refresh_from_db()
        assert cand.current_state == 'ONBOARDED'

    def test_withdraw_still_broken(self, hr_user):
        cand = _mk(name='BUG5撤回', phone='13900001010')
        try:
            CandidateService.withdraw(cand, reason='r', actor=hr_user)
        except (AttributeError, StateTransitionError) as e:
            pytest.xfail(f'BUG-5 未修 (工程师已上报, 待 FSM 设计决策): {e}')
        cand.refresh_from_db()
        assert cand.current_state == 'WITHDRAWN'
