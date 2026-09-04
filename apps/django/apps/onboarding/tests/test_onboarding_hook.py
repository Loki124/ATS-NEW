"""Onboarding 钩子端到端集成测试（v2.10 T03：人员比例管控 → Onboarding 节点 4 / 5）。

直接驱动 ``OnboardingService.create_onboarding`` 与 ``OnboardingService.mark_completed``
（即被视图调用的同一入口），验证：
  - 硬约束命中 → 抛 ``rest_framework.exceptions.ValidationError``（HTTP 400），
    且事务回滚、Onboarding 不落库（节点 4）/ 状态不变（节点 5）。
  - 软约束命中 → 放行，Onboarding 正常落库 / 状态推进。

计数口径复用 calc.py（由 services.validate_offer_against_rules 内部保证），
此处只验证「钩子是否被正确接入 onboarding 4/5 节点并触发阻断/放行」。

v2.10 关键差异：开启 rollover_enabled 时，校验口径切换为
「monthTarget + monthRollover」（与 v2.4「仅 monthTarget」零回归对照）。
"""
import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.application.models import Application
from apps.campus_control.models import ControlDimension, ControlIndicator, ControlRule, Person
from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.offer.models import Offer, OfferState
from apps.offer.services import OfferCreateData, OfferService
from apps.onboarding.models import Onboarding, OnboardingState
from apps.onboarding.services import OnboardingCreateData, OnboardingService
from apps.position.models import Position
from apps.process.models import RecruitmentProcess

pytestmark = pytest.mark.django_db(transaction=True)


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _build_onboarding_scenario(strength: str, rollover_enabled: bool):
    """造真实 Department/User/Process/Position/Candidate/Offer + 一条硬/软约束规则。

    规则：维度=性别，指标=男，bu=能电BG（= position.department.name），
    annual_target=1（合成 offer 自身即第 1 人，必然命中），strength/rollover_enabled 由参数决定。
    monthly = 9 月 = 1（curMonth=9 → 月目标 1；rollover_enabled 开启时，monthAvailableTarget = 1 + 0 = 1）。

    返回 (data: OnboardingCreateData, rule: ControlRule, offer: Offer, user)。
    """
    # 隔离：清掉可能由 --reuse-db 累积的 Person / ControlRule，保证计数确定性。
    Person.objects.all().delete()
    ControlRule.objects.all().delete()

    User = get_user_model()
    user = User.objects.create_user(username=_uid("hr_ob"), password="Test@1234")

    dept = Department.objects.create(
        id=_uid("dept"), name="能电BG", code=_uid("NEDOB"),
    )
    process = RecruitmentProcess.objects.create(
        code=_uid("PROC"), name="测试流程OB", current_version="V1.0",
        version_seq=1, is_latest=True,
    )
    position = Position.objects.create(
        code=_uid("POS"), title="测试职位OB", department=dept,
        hiring_manager=user, owner=user, process=process,
    )
    candidate = Candidate.objects.create(
        name="测试候选人OB", phone=_uid("138"),
        gender="男", school_tag="985", major_tag="工学",
    )
    application = Application.objects.create(
        code=_uid("APP"), candidate=candidate, position=position,
        process=process, workflow_version="V1.0",
    )

    dim = ControlDimension.objects.create(name="性别")
    ind = ControlIndicator.objects.create(dimension=dim, name="男")
    rule = ControlRule.objects.create(
        dimension=dim, indicator=ind, year=2026,
        target=Decimal("1"), strength=strength,
        annual_target=1, monthly_targets=[0] * 8 + [1] + [0] * 3,
        bu="能电BG", position="", level="",
        rollover_enabled=rollover_enabled,
    )

    # 构造 Offer（绕过 create_offer 的钩子——本测试只验证 Onboarding 钩子，不依赖 Offer 钩子）
    offer = Offer.objects.create(
        code=_uid("OFR"),
        application=application, candidate=candidate, position=position,
        salary=10000.0,
        start_date="2026-09-15",
        expire_date="2026-10-15",
        level="L1",
        position_title="研发工程师",
        state=OfferState.DRAFT,
        created_by=user, updated_by=user,
    )

    data = OnboardingCreateData(
        offer_id=offer.id,
        candidate_id=candidate.id,
        position_id=position.id,
        start_date="2026-09-15",
        actor=user,
    )
    return data, rule, offer, user


def test_create_onboarding_hard_block_rolls_back():
    """v2.10 节点 4 (create_onboarding) + 硬约束 → 400 + Onboarding 不落库。"""
    data, rule, offer, user = _build_onboarding_scenario("硬约束", rollover_enabled=True)
    with pytest.raises(DRFValidationError) as exc:
        OnboardingService.create_onboarding(data)
    assert "硬约束" in str(exc.value.detail)
    # 阻断 → 事务回滚 → 无 Onboarding 行
    assert Onboarding.objects.count() == 0
    # Offer 状态应保持 DRAFT（阻断未影响 Offer，仅阻断 Onboarding 创建）
    offer.refresh_from_db()
    assert offer.state == OfferState.DRAFT


def test_create_onboarding_soft_warn_passes():
    """v2.10 节点 4 (create_onboarding) + 软约束 → 放行，Onboarding 正常落库。"""
    data, rule, offer, user = _build_onboarding_scenario("软约束", rollover_enabled=False)
    ob = OnboardingService.create_onboarding(data)
    assert isinstance(ob, Onboarding)
    assert Onboarding.objects.count() == 1
    assert ob.candidate_id == data.candidate_id
    assert ob.position_id == data.position_id
    assert ob.state == OnboardingState.PENDING


def test_mark_completed_hard_block_rolls_back():
    """v2.10 节点 5 (mark_completed) + 硬约束 → 400 + state 不变（仍为 PREPARING）。

    mark_completed 依赖 Onboarding 处于 PREPARING 状态（complete() 的 FSM transition）。
    本测试先用 create_onboarding 落入 PENDING，再 start_preparing 推到 PREPARING，
    然后 mark_completed → 阻断 → state 应保持 PREPARING（事务回滚）。
    """
    # 软约束场景下先正常创建 + 推到 PREPARING（不触发硬约束）；然后手动换一条硬约束。
    # 简化：直接构造 PENDING + PREPARING 状态的 onboarding，避免 OnboardingService 钩子阻断 create 阶段。
    Person.objects.all().delete()
    ControlRule.objects.all().delete()

    User = get_user_model()
    user = User.objects.create_user(username=_uid("hr_mc"), password="Test@1234")
    dept = Department.objects.create(id=_uid("dept_mc"), name="能电BG", code=_uid("NMC"))
    process = RecruitmentProcess.objects.create(
        code=_uid("PROC_MC"), name="P", current_version="V1.0",
        version_seq=1, is_latest=True,
    )
    position = Position.objects.create(
        code=_uid("POS_MC"), title="T", department=dept,
        hiring_manager=user, owner=user, process=process,
    )
    candidate = Candidate.objects.create(
        name="C", phone=_uid("138"), gender="男", school_tag="985", major_tag="工学",
    )
    application = Application.objects.create(
        code=_uid("APP_MC"), candidate=candidate, position=position,
        process=process, workflow_version="V1.0",
    )
    offer = Offer.objects.create(
        code=_uid("OFR_MC"),
        application=application, candidate=candidate, position=position,
        salary=10000.0, start_date="2026-09-15", expire_date="2026-10-15",
        level="L1", position_title="研发工程师",
        state=OfferState.SENT,
        created_by=user, updated_by=user,
    )
    # 直接构造 Onboarding（绕过 create_onboarding 钩子，避免阻断）
    from datetime import date as _DDate
    ob = Onboarding.objects.create(
        offer=offer, candidate=candidate, position=position,
        start_date=_DDate(2026, 9, 15),
        todo_list=['t1'], todo_completed={'t1': False},
        state=OnboardingState.PREPARING,
        created_by=user, updated_by=user,
    )
    # 再创建硬约束 + rollover_enabled（用于触发阻断）
    dim = ControlDimension.objects.create(name="性别")
    ind = ControlIndicator.objects.create(dimension=dim, name="男")
    ControlRule.objects.create(
        dimension=dim, indicator=ind, year=2026,
        target=Decimal("1"), strength="硬约束",
        annual_target=1, monthly_targets=[0] * 8 + [1] + [0] * 3,
        bu="能电BG", position="", level="",
        rollover_enabled=True,
    )
    # mark_completed → 触发硬约束
    with pytest.raises(DRFValidationError) as exc:
        OnboardingService.mark_completed(ob.id, user)
    assert "硬约束" in str(exc.value.detail)
    ob.refresh_from_db()
    # 阻断 → state 应保持 PREPARING（事务回滚）
    assert ob.state == OnboardingState.PREPARING


def test_mark_completed_soft_warn_passes():
    """v2.10 节点 5 (mark_completed) + 软约束 → 放行，state 推进到 COMPLETED。"""
    Person.objects.all().delete()
    ControlRule.objects.all().delete()

    User = get_user_model()
    user = User.objects.create_user(username=_uid("hr_sw"), password="Test@1234")
    dept = Department.objects.create(id=_uid("dept_sw"), name="能电BG", code=_uid("NSW"))
    process = RecruitmentProcess.objects.create(
        code=_uid("PROC_SW"), name="P", current_version="V1.0",
        version_seq=1, is_latest=True,
    )
    position = Position.objects.create(
        code=_uid("POS_SW"), title="T", department=dept,
        hiring_manager=user, owner=user, process=process,
    )
    candidate = Candidate.objects.create(
        name="C", phone=_uid("138"), gender="男", school_tag="985", major_tag="工学",
    )
    application = Application.objects.create(
        code=_uid("APP_SW"), candidate=candidate, position=position,
        process=process, workflow_version="V1.0",
    )
    offer = Offer.objects.create(
        code=_uid("OFR_SW"),
        application=application, candidate=candidate, position=position,
        salary=10000.0, start_date="2026-09-15", expire_date="2026-10-15",
        level="L1", position_title="研发工程师",
        state=OfferState.SENT,
        created_by=user, updated_by=user,
    )
    from datetime import date as _DDate
    ob = Onboarding.objects.create(
        offer=offer, candidate=candidate, position=position,
        start_date=_DDate(2026, 9, 15),
        todo_list=['t1'], todo_completed={'t1': False},
        state=OnboardingState.PREPARING,
        created_by=user, updated_by=user,
    )
    # 软约束
    dim = ControlDimension.objects.create(name="性别")
    ind = ControlIndicator.objects.create(dimension=dim, name="男")
    ControlRule.objects.create(
        dimension=dim, indicator=ind, year=2026,
        target=Decimal("1"), strength="软约束",
        annual_target=1, monthly_targets=[0] * 8 + [1] + [0] * 3,
        bu="能电BG", position="", level="",
        rollover_enabled=False,
    )
    # mark_completed → 软约束命中 → 仅 logger.warning 放行
    ob_after = OnboardingService.mark_completed(ob.id, user)
    assert ob_after.state == OnboardingState.COMPLETED