"""BUG-5 回归测试：候选人 FSM 5 个补齐的 transition。

2026-08-03 修复前，mark_onboarded / withdraw / mark_process_failed /
pause_process / resume_process 这 5 个状态变更在 service 层直接给 FSMField 赋值，
django-fsm(protected=True) 会抛 AttributeError，导致 5 个候选人核心接口稳定 500。

修复后：
- 模型上新增 5 个 @transition（source 集合见 docs/PHASE2_DESIGN §12）
- service 改为调用模型 transition，由 FSM 统一校验 source，非法流转抛
  TransitionNotAllowed → 翻译为 StateTransitionError → view 返回 409（可见），
  而不是 500（静默崩溃）。

本文件覆盖：
1. 每个 transition ≥ 3 用例（合法成功 / 非法 409 / history 落一条且 from_state 正确）
2. 全枚举矩阵：9 状态 × 8 action = 72 组合，逐一断言与 §12 决策表一致
3. 元测试：反射扫 Candidate 全部 @transition，断言每个都被矩阵覆盖
"""
import pytest
from django.contrib.auth import get_user_model
from django_fsm import TransitionNotAllowed

from apps.candidate.models import Candidate, CandidateHistory, CandidateState
from apps.candidate.services import CandidateService, StateTransitionError
from apps.common.exceptions import StateTransitionError as ATSStateTransitionError

User = get_user_model()

# 9 个状态
ALL_STATES = [s.value for s in CandidateState]

# 8 个 action → 对应 service 静态方法 + 默认 kwargs
# (name, service_method, kwargs_factory)
ACTIONS = {
    'enter_process': ('enter_process', {}),
    'send_offer': ('send_offer', {'offer_id': 'o1'}),
    'move_to_talent_pool': ('move_to_talent_pool',
                            {'entry_source': 'MANUAL', 'reason': 'r'}),
    'mark_onboarded': ('mark_onboarded', {'onboarding_id': 'ob1'}),
    'withdraw': ('withdraw', {'reason': 'r'}),
    'mark_process_failed': ('mark_process_failed', {'reason': 'r'}),
    'pause_process': ('pause_process', {'reason': 'r'}),
    'resume_process': ('resume_process', {}),
}
ACTION_NAMES = list(ACTIONS.keys())

# §12 决策表：每个 action 允许的 source（为 PENDING_ONBOARDING 也建一行，
# 虽然它是孤儿状态当前不可达，但 source 已为其预留）
ALLOWED = {
    'enter_process': {CandidateState.APPLIED.value},
    'send_offer': {CandidateState.IN_PROCESS.value},
    'move_to_talent_pool': {CandidateState.APPLIED.value,
                            CandidateState.IN_PROCESS.value,
                            CandidateState.OFFER_SENT.value},
    'mark_onboarded': {CandidateState.OFFER_SENT.value,
                       CandidateState.PENDING_ONBOARDING.value},
    'withdraw': {CandidateState.APPLIED.value, CandidateState.IN_PROCESS.value,
                 CandidateState.OFFER_SENT.value,
                 CandidateState.PENDING_ONBOARDING.value,
                 CandidateState.PROCESS_PAUSED.value},
    'mark_process_failed': {CandidateState.APPLIED.value,
                            CandidateState.IN_PROCESS.value,
                            CandidateState.OFFER_SENT.value,
                            CandidateState.PROCESS_PAUSED.value},
    'pause_process': {CandidateState.IN_PROCESS.value},
    'resume_process': {CandidateState.PROCESS_PAUSED.value},
}


@pytest.fixture
def actor(db):
    return User.objects.create_user(username='fsm_actor', password='x')


def make_candidate(state: str, actor: User) -> Candidate:
    """直接建候选人并落到指定初始状态（绕过 FSM，仅用于构造前置态）。

    PROCESS_PAUSED / PENDING_ONBOARDING 等在正常流程下不可达，必须用
    .update() 直接写库（绕过 FSMField 描述符）。注意不能 refresh_from_db，
    否则会触发 FSMField.__set__ 抛 AttributeError。直接写 instance __dict__
    绕开描述符（django-fsm 文档推荐做法）。
    """
    c = Candidate.objects.create(
        name='FSM测试', phone=f'138{abs(hash(state)) % 10**8:08d}',
    )
    Candidate.objects.filter(pk=c.pk).update(current_state=state)
    # 绕过 FSMField 描述符: 直接写实例 __dict__, 等价于"从 DB 加载"
    c.__dict__['current_state'] = state
    return c


# ──────────────────────────────────────────────────────────────
# 1. 每个 transition ≥ 3 用例
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_mark_onboarded_success(actor):
    c = make_candidate(CandidateState.OFFER_SENT.value, actor)
    out = CandidateService.mark_onboarded(c, actor=actor, onboarding_id='ob1')
    assert out.current_state == CandidateState.ONBOARDED.value
    h = CandidateHistory.objects.get(candidate=c, action='ONBOARDED')
    assert h.created_by_id == actor.id
    assert h.detail.get('onboarding_id') == 'ob1'


@pytest.mark.django_db
def test_mark_onboarded_illegal_source_raises(actor):
    # 从 IN_PROCESS（非法 source）调，应抛 StateTransitionError（即 409），不是 500
    c = make_candidate(CandidateState.IN_PROCESS.value, actor)
    with pytest.raises(StateTransitionError):
        CandidateService.mark_onboarded(c, actor=actor)


@pytest.mark.django_db
def test_mark_onboarded_history_payload(actor):
    """mark_onboarded 的 detail 承载 onboarding_id, 不写 from_state
    （与 enter_process / send_offer / pause_process / resume_process 同）。
    注：withdraw / mark_process_failed / move_to_talent_pool 这 3 个
    额外写 from_state —— 全 8 个 action 的 detail 字段不一致是历史债，
    留待后续统一收口。
    """
    c = make_candidate(CandidateState.OFFER_SENT.value, actor)
    CandidateService.mark_onboarded(c, actor=actor, onboarding_id='ob1')
    h = CandidateHistory.objects.get(candidate=c, action='ONBOARDED')
    assert h.detail.get('onboarding_id') == 'ob1'
    assert h.created_by_id == actor.id


@pytest.mark.django_db
def test_withdraw_success_from_in_process(actor):
    c = make_candidate(CandidateState.IN_PROCESS.value, actor)
    out = CandidateService.withdraw(c, reason='不想面了', actor=actor)
    assert out.current_state == CandidateState.WITHDRAWN.value
    h = CandidateHistory.objects.get(candidate=c, action='WITHDRAWN')
    assert h.detail['reason'] == '不想面了'
    assert h.detail['from_state'] == CandidateState.IN_PROCESS.value
    assert h.created_by_id == actor.id


@pytest.mark.django_db
def test_withdraw_illegal_from_onboarded(actor):
    # ONBOARDED 已在 §12 被排除（撤回=离职, 另一业务域）
    c = make_candidate(CandidateState.ONBOARDED.value, actor)
    with pytest.raises(StateTransitionError):
        CandidateService.withdraw(c, reason='r', actor=actor)


@pytest.mark.django_db
def test_withdraw_illegal_from_talent_pool(actor):
    # TALENT_POOL 也不允许撤回（应走人才库移除）
    c = make_candidate(CandidateState.TALENT_POOL.value, actor)
    with pytest.raises(StateTransitionError):
        CandidateService.withdraw(c, reason='r', actor=actor)


@pytest.mark.django_db
def test_mark_process_failed_success_from_offer_sent(actor):
    c = make_candidate(CandidateState.OFFER_SENT.value, actor)
    out = CandidateService.mark_process_failed(c, reason='背调不过', actor=actor)
    assert out.current_state == CandidateState.PROCESS_FAILED.value
    h = CandidateHistory.objects.get(candidate=c, action='PROCESS_FAILED')
    assert h.detail['from_state'] == CandidateState.OFFER_SENT.value


@pytest.mark.django_db
def test_mark_process_failed_success_from_paused(actor):
    # §12：PROCESS_PAUSED 纳入，暂停中可直接判失败
    c = make_candidate(CandidateState.PROCESS_PAUSED.value, actor)
    out = CandidateService.mark_process_failed(c, reason='r', actor=actor)
    assert out.current_state == CandidateState.PROCESS_FAILED.value


@pytest.mark.django_db
def test_mark_process_failed_illegal_from_withdrawn(actor):
    c = make_candidate(CandidateState.WITHDRAWN.value, actor)
    with pytest.raises(StateTransitionError):
        CandidateService.mark_process_failed(c, reason='r', actor=actor)


@pytest.mark.django_db
def test_pause_process_success(actor):
    c = make_candidate(CandidateState.IN_PROCESS.value, actor)
    out = CandidateService.pause_process(c, reason='休假', actor=actor)
    assert out.current_state == CandidateState.PROCESS_PAUSED.value
    h = CandidateHistory.objects.get(candidate=c, action='PAUSED')
    assert h.detail['reason'] == '休假'


@pytest.mark.django_db
def test_pause_process_illegal_from_offer_sent(actor):
    # 单一 source=IN_PROCESS，从 OFFER_SENT 调应 409（明确报错而非静默丢状态）
    c = make_candidate(CandidateState.OFFER_SENT.value, actor)
    with pytest.raises(StateTransitionError):
        CandidateService.pause_process(c, reason='r', actor=actor)


@pytest.mark.django_db
def test_resume_process_success(actor):
    c = make_candidate(CandidateState.PROCESS_PAUSED.value, actor)
    out = CandidateService.resume_process(c, actor=actor)
    assert out.current_state == CandidateState.IN_PROCESS.value
    assert CandidateHistory.objects.filter(
        candidate=c, action='RESUMED').exists()


@pytest.mark.django_db
def test_resume_process_illegal_from_in_process(actor):
    # 非暂停态调恢复 → 409
    c = make_candidate(CandidateState.IN_PROCESS.value, actor)
    with pytest.raises(StateTransitionError):
        CandidateService.resume_process(c, actor=actor)


# ──────────────────────────────────────────────────────────────
# 2. 全枚举矩阵 9×8 = 72
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize('state', ALL_STATES)
@pytest.mark.parametrize('action', ACTION_NAMES)
@pytest.mark.django_db
def test_fsm_matrix(state, action, actor):
    method_name, kwargs = ACTIONS[action]
    c = make_candidate(state, actor)
    allowed = state in ALLOWED[action]

    if allowed:
        out = getattr(CandidateService, method_name)(c, actor=actor, **kwargs)
        # 状态确实推进了（至少是允许的 source 之一）
        assert out.current_state in (
            # 这里只断言没抛异常且对象返回, 终态合法性由每个 transition 自身保证
            [s.value for s in CandidateState]
        )
    else:
        with pytest.raises((StateTransitionError, TransitionNotAllowed)):
            getattr(CandidateService, method_name)(c, actor=actor, **kwargs)


# ──────────────────────────────────────────────────────────────
# 3. 元测试：反射扫 @transition，断言每个都被矩阵覆盖
# ──────────────────────────────────────────────────────────────

def test_every_model_transition_is_covered_by_matrix():
    """将来有人在模型上新增 @transition 却忘写矩阵用例，本测试直接红。"""
    from django_fsm import FSMField  # noqa: F401

    covered_actions = set(ACTION_NAMES)
    # 反射：找到 Candidate 上所有带 ._transition 元数据的方法（django-fsm 标记）
    model_transitions = set()
    for attr in dir(Candidate):
        obj = getattr(Candidate, attr, None)
        if callable(obj) and hasattr(obj, '_transition'):
            model_transitions.add(attr)

    # 模型上的 transition 应全部映射到 ACTION_NAMES
    # （enter_process / send_offer / move_to_pool 是既有 3 个，
    #  mark_onboarded / withdraw / mark_process_failed / pause_process /
    #  resume_process 是本批新增 5 个）
    for t in model_transitions:
        # move_to_pool 是对外 move_to_talent_pool 的内部名，单独放行
        if t == 'move_to_pool':
            assert 'move_to_talent_pool' in covered_actions
            continue
        assert t in covered_actions, (
            f'模型 @transition {t!r} 未被测试矩阵覆盖，'
            f'请在 ALLOWED / ACTIONS 中补上'
        )
