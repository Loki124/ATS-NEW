"""Offer 钩子端到端集成测试（T03：人员比例管控 → Offer 创建拦截）。

直接驱动 ``OfferService.create_offer``（即被视图调用的同一入口），
验证：
  - 硬约束命中 → 抛 ``rest_framework.exceptions.ValidationError``（HTTP 400），
    且事务回滚、Offer 不落库。
  - 软约束命中 → 放行，Offer 正常落库。

计数口径复用 calc.py（由 services.validate_offer_against_rules 内部保证），
此处只验证「钩子是否被正确接入 create_offer 并触发阻断/放行」。
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
from apps.offer.models import Offer
from apps.offer.services import OfferCreateData, OfferService
from apps.position.models import Position
from apps.process.models import RecruitmentProcess

pytestmark = pytest.mark.django_db(transaction=True)


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _build_scenario(strength: str):
    """造真实 Department/User/Process/Position/Candidate/Application + 一条硬/软约束规则。

    规则：维度=性别，指标=男，bu=能电BG（= position.department.name），
    annual_target=1（合成 offer 自身即第 1 人，必然命中），strength 由参数决定。
    返回 (data: OfferCreateData, rule: ControlRule)。
    """
    # 隔离：清掉可能由 --reuse-db 累积的 Person / ControlRule，保证计数确定性。
    Person.objects.all().delete()
    ControlRule.objects.all().delete()

    User = get_user_model()
    user = User.objects.create_user(username=_uid("hr"), password="Test@1234")

    dept = Department.objects.create(
        id=_uid("dept"), name="能电BG", code=_uid("NED"),
    )
    process = RecruitmentProcess.objects.create(
        code=_uid("PROC"), name="测试流程", current_version="V1.0",
        version_seq=1, is_latest=True,
    )
    position = Position.objects.create(
        code=_uid("POS"), title="测试职位", department=dept,
        hiring_manager=user, owner=user, process=process,
    )
    candidate = Candidate.objects.create(
        name="测试候选人", phone=_uid("138"),
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
        annual_target=1, monthly_targets=[0] * 12,
        bu="能电BG", position="", level="",
    )

    data = OfferCreateData(
        application_id=application.id,
        candidate_id=candidate.id,
        position_id=position.id,
        salary=10000.0,
        start_date="2026-08-15",
        expire_date="2026-09-15",
        level="L1",
        position_title="研发工程师",
        actor=user,
    )
    return data, rule


def test_offer_hook_hard_block_rolls_back():
    """硬约束命中 → 抛 400 ValidationError，且无 Offer 落库。"""
    data, _ = _build_scenario("硬约束")

    with pytest.raises(DRFValidationError) as exc:
        OfferService.create_offer(data)

    # 断言异常结构：detail 含命中规则明细（services 转成 {'detail': msg}）
    assert "硬约束" in str(exc.value.detail)
    # 事务回滚 / 钩子在 Offer.objects.create 之前抛出 → 无 Offer 行
    assert Offer.objects.count() == 0


def test_offer_hook_soft_warn_passes_and_creates_offer():
    """软约束命中 → 放行，Offer 正常落库。"""
    data, _ = _build_scenario("软约束")

    offer = OfferService.create_offer(data)

    assert isinstance(offer, Offer)
    assert Offer.objects.count() == 1
    assert offer.candidate_id == data.candidate_id
    assert offer.position_id == data.position_id
