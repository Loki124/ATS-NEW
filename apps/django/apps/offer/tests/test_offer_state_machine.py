"""Offer 状态机全量测试.

背景 (2026-10-08 审查):
    `Offer.state` 是 `FSMField(protected=True)` (models.py:70-73), 定义了 9 个
    @transition (models.py:87-127)。但测试只有 test_offer_hook.py 覆盖了
    create / submit_approval / send 的硬约束拦截, **approve / reject / send /
    accept / negotiate / candidate_reject / set_onboarding_date / onboarded
    共 8 个迁移零测试** —— Offer 是录用流程的最后一环, 状态错乱直接导致
    发错 Offer 或漏入职。

本文件覆盖:
    1. 9 个迁移的 source → target 全量验证
    2. 各迁移的副作用字段 (approved_at / sent_at / responded_at / start_date …)
    3. 非法 source 必须抛 TransitionNotAllowed, 且状态不变
    4. protected=True: 禁止直接赋值绕过状态机
"""
from datetime import date

import pytest
from django_fsm import TransitionNotAllowed, can_proceed

from apps.application.models import Application
from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.offer.models import Offer, OfferState
from apps.position.models import Position
from apps.process.models import RecruitmentProcess

# ---------------------------------------------------------------- 构造链

def _set_state(offer, state):
    """把 Offer 直接置到指定状态。

    state 是 protected=True 的 FSMField, 直接赋值会抛 AttributeError;
    用 queryset.update 绕过 ORM 层的保护来构造前置状态。
    """
    Offer.objects.filter(pk=offer.pk).update(state=state)
    offer.refresh_from_db()
    return offer


@pytest.fixture
def offer(db, hr_user):
    """构造一条 DRAFT 状态的 Offer (Department→Position→Candidate→Process→Application)。"""
    dept = Department.objects.create(id='dept-offer', name='Offer部门', code='offer_dept')
    process = RecruitmentProcess.objects.create(
        id='proc-offer', code='PROC-OFFER', name='Offer测试流程',
        current_version='1.0', is_template=False, is_enabled=True, is_latest=True,
    )
    position = Position.objects.create(
        code='POS-OFFER', title='Offer测试职位', department=dept,
        hiring_manager=hr_user, owner=hr_user, process=process,
    )
    candidate = Candidate.objects.create(
        id='cand-offer', name='Offer候选人', phone='13800003001', created_by=hr_user,
    )
    application = Application.objects.create(
        code='APP-OFFER', candidate=candidate, position=position, process=process,
    )
    return Offer.objects.create(
        code='OFFER-SM-001',
        application=application,
        candidate=candidate,
        position=position,
    )


# ---------------------------------------------------------------- 9 个迁移

@pytest.mark.django_db
def test_submit_approval(offer):
    """DRAFT → PENDING_APPROVAL"""
    assert offer.state == OfferState.DRAFT
    assert can_proceed(offer.submit_approval) is True

    offer.submit_approval()
    offer.save()
    assert offer.state == OfferState.PENDING_APPROVAL


@pytest.mark.django_db
def test_approve_sets_approved_at(offer):
    """PENDING_APPROVAL → PENDING_SEND, 并写入审批时间"""
    _set_state(offer, OfferState.PENDING_APPROVAL)
    assert offer.approved_at is None

    offer.approve()
    offer.save()
    assert offer.state == OfferState.PENDING_SEND
    assert offer.approved_at is not None


@pytest.mark.django_db
def test_reject(offer):
    """PENDING_APPROVAL → REJECTED"""
    _set_state(offer, OfferState.PENDING_APPROVAL)

    offer.reject()
    offer.save()
    assert offer.state == OfferState.REJECTED


@pytest.mark.django_db
def test_send_sets_sent_at(offer):
    """PENDING_SEND → SENT, 并写入发送时间"""
    _set_state(offer, OfferState.PENDING_SEND)
    assert offer.sent_at is None

    offer.send()
    offer.save()
    assert offer.state == OfferState.SENT
    assert offer.sent_at is not None


@pytest.mark.django_db
def test_accept_sets_responded_at(offer):
    """SENT → ACCEPTED, 并写入响应时间"""
    _set_state(offer, OfferState.SENT)

    offer.accept()
    offer.save()
    assert offer.state == OfferState.ACCEPTED
    assert offer.responded_at is not None


@pytest.mark.django_db
def test_negotiate(offer):
    """SENT → NEGOTIATING, 并写入响应时间"""
    _set_state(offer, OfferState.SENT)

    offer.negotiate()
    offer.save()
    assert offer.state == OfferState.NEGOTIATING
    assert offer.responded_at is not None


@pytest.mark.django_db
def test_candidate_reject_records_reason(offer):
    """SENT → REJECTED_BY_CANDIDATE, 并记录拒绝原因"""
    _set_state(offer, OfferState.SENT)

    offer.candidate_reject(reason='薪资未达成一致')
    offer.save()
    assert offer.state == OfferState.REJECTED_BY_CANDIDATE
    assert offer.responded_at is not None
    assert offer.rejection_reason == '薪资未达成一致'


@pytest.mark.django_db
def test_set_onboarding_date(offer):
    """ACCEPTED → PENDING_ONBOARDING, 并写入入职日期"""
    _set_state(offer, OfferState.ACCEPTED)
    target = date(2026, 12, 1)

    offer.set_onboarding_date(target)
    offer.save()
    assert offer.state == OfferState.PENDING_ONBOARDING
    assert offer.start_date == target


@pytest.mark.django_db
def test_onboarded(offer):
    """PENDING_ONBOARDING → ONBOARDED"""
    _set_state(offer, OfferState.PENDING_ONBOARDING)

    offer.onboarded()
    offer.save()
    assert offer.state == OfferState.ONBOARDED


# ---------------------------------------------------------------- 非法迁移

@pytest.mark.django_db
@pytest.mark.parametrize('method_name,setup_state', [
    ('submit_approval', OfferState.SENT),          # 只能从 DRAFT 提交
    ('approve', OfferState.DRAFT),                 # 只能审批待审批的
    ('reject', OfferState.SENT),                   # 已发出的不能驳回
    ('send', OfferState.DRAFT),                    # 草稿不能直接发出
    ('accept', OfferState.DRAFT),                  # 只有已发出才能接受
    ('negotiate', OfferState.ACCEPTED),            # 已接受的不能再谈判
    ('candidate_reject', OfferState.DRAFT),        # 草稿不存在候选人拒绝
    ('onboarded', OfferState.SENT),                # 只有待入职才能置为已入职
])
def test_illegal_transition_rejected(offer, method_name, setup_state):
    """非法 source 必须抛 TransitionNotAllowed, 且状态保持不变 (不能静默变脏)。"""
    _set_state(offer, setup_state)
    before = offer.state

    assert can_proceed(getattr(offer, method_name)) is False
    with pytest.raises(TransitionNotAllowed):
        getattr(offer, method_name)()

    offer.refresh_from_db()
    assert offer.state == before, '非法迁移不得改变状态'


@pytest.mark.django_db
def test_set_onboarding_date_illegal_source(offer):
    """set_onboarding_date 带参数, 单独验证非法 source。"""
    _set_state(offer, OfferState.SENT)
    with pytest.raises(TransitionNotAllowed):
        offer.set_onboarding_date(date(2026, 12, 1))
    offer.refresh_from_db()
    assert offer.state == OfferState.SENT


# ---------------------------------------------------------------- 保护机制

@pytest.mark.django_db
def test_state_cannot_be_assigned_directly(offer):
    """protected=True: 禁止绕过状态机直接改状态。"""
    with pytest.raises(AttributeError):
        offer.state = OfferState.ONBOARDED

    offer.refresh_from_db()
    assert offer.state == OfferState.DRAFT


@pytest.mark.django_db
def test_happy_path_walks_all_the_way_to_onboarded(offer):
    """端到端走通主流程: DRAFT → … → ONBOARDED, 每一步都必须是合法迁移。

    比内省 FSM 元数据更可靠: 一旦有人改了某个 transition 的 source/target,
    这条链会立刻断在这里, 而不是等到线上发错 Offer 才发现。
    """
    assert offer.state == OfferState.DRAFT

    offer.submit_approval(); offer.save()
    assert offer.state == OfferState.PENDING_APPROVAL

    offer.approve(); offer.save()
    assert offer.state == OfferState.PENDING_SEND

    offer.send(); offer.save()
    assert offer.state == OfferState.SENT

    offer.accept(); offer.save()
    assert offer.state == OfferState.ACCEPTED

    offer.set_onboarding_date(date(2026, 12, 1)); offer.save()
    assert offer.state == OfferState.PENDING_ONBOARDING

    offer.onboarded(); offer.save()
    assert offer.state == OfferState.ONBOARDED

    # 终态: 已入职后不能再回退或重复迁移
    assert can_proceed(offer.onboarded) is False
    assert can_proceed(offer.accept) is False
