"""P0 回归：申请三条核心路径经过限时计算时必然崩溃（2026-08-11）

背景：672 个测试全绿，而创建申请这个接口在生产上必然 500
========================================================
``ApplicationService`` 有三处调用 ``calc_time_limit``，且**全是裸调用、无 try/except**：

===============================================  =========================================
服务方法                                          对外端点
===============================================  =========================================
``create_application``            (:171)          ``POST /api/v1/applications/``
``advance_application_to_next_stage`` (:399)      ``POST /api/v1/applications/{id}/advance/``
``jump_application_to_stage``     (:539)          ``POST /api/v1/applications/{id}/jump/``
===============================================  =========================================

另有 ``automation/services.py`` 两处自动化调用同样经过这里。

这三条路径上串着两颗必炸的雷：

1. ``calc_time_limit`` 过滤 ``deleted_at__isnull=True``，而 ``TimeLimitRule``
   当时**没有这个字段** → 每次调用抛 ``FieldError``。
2. 就算绕过第一颗，紧接着的 ``tl.total_days`` 也不存在 ——
   ``TimeLimitCalcResult`` 的字段叫 ``total_lock_days``，
   全仓共 12 处误写 → ``AttributeError``。

之所以 672 个测试全绿，是因为**没有任何一条测试真的走完这三条路径**。
这是"假绿"的典型形态：测试数量看着体面，核心链路一步没踩。

本文件的职责就是把这三条路径钉在地上：每条都真的跑一遍服务层，
并断言限时结果确实被写进了申请与阶段记录。

变异自证（靶心）
================
* 把 ``TimeLimitRule`` 的 ``SoftDeleteModel`` 基类去掉 → 本文件**全红**（FieldError）。
* 把 ``services/__init__.py`` 里任意一处 ``tl.total_lock_days`` 改回 ``tl.total_days``
  → 对应路径的用例转红（AttributeError）。
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from apps.application.models import Application, ApplicationHistory, ApplicationStageRecord
from apps.application.services import ApplicationCreateData, ApplicationService
from apps.candidate.models import Candidate
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageType,
)
from apps.time_limit.models import TimeLimitRule

pytestmark = pytest.mark.django_db


# ============================================================
# Seed（dev 库 Application=0，一切自建）
# ============================================================
def _reload(application: Application) -> Application:
    """重新查库。不能用 refresh_from_db —— Application.state 是受保护的 FSMField，
    refresh 时会走 FSMField.__set__ 抛 AttributeError('Direct state modification
    is not allowed')。仓库既有测试（test_change_process.py:90、
    test_upgrade_workflow_version.py:98）用的也是这个 helper。
    """
    return Application.objects.get(pk=application.pk)


def _stage(code: str, name: str) -> RecruitmentStage:
    stage, _ = RecruitmentStage.objects.get_or_create(
        code=code, defaults={'name': name, 'stage_type': StageType.SCREEN},
    )
    return stage


def _rule(link: ProcessStageLink, *, name: str, days: int, per_person: int = 0) -> TimeLimitRule:
    return TimeLimitRule.objects.create(
        link=link, process_id='', workflow_version='',
        rule_name=name, conditions=[], lock_duration=days,
        extension_per_person=per_person, priority=0, enabled=True,
    )


@pytest.fixture
def two_stage_process(db):
    """两阶段流程：初筛(order=1) → 面试(order=2)。"""
    process = RecruitmentProcess.objects.create(
        code='TLINTEG', name='限时集成测试流程', current_version='V1.0',
        version_seq=1, is_latest=True, status='ENABLED',
    )
    link1 = ProcessStageLink.objects.create(
        process=process, stage=_stage('TLI1', '限时初筛'), order=1, is_required=True,
    )
    link2 = ProcessStageLink.objects.create(
        process=process, stage=_stage('TLI2', '限时面试'), order=2, is_required=True,
    )
    return process, link1, link2


@pytest.fixture
def recruiting_position(db, two_stage_process, department, super_user) -> Position:
    process, _, _ = two_stage_process
    position = Position.objects.create(
        code='POS_TLINTEG', title='限时集成职位', description='x',
        department=department, hiring_manager=super_user, owner=super_user,
        headcount=1, state=PositionState.DRAFT, process=process,
    )
    position.submit_publish(); position.save()
    position.publish(); position.save()
    position.start_recruiting(); position.save()
    return position


@pytest.fixture
def candidate(db) -> Candidate:
    return Candidate.objects.create(name='限时集成候选人', phone='13980000001')


# ============================================================
# 1. create_application —— POST /api/v1/applications/
# ============================================================
def test_create_application_completes_and_writes_time_limit(
    two_stage_process, recruiting_position, candidate,
) -> None:
    """创建申请必须跑通，且首阶段的限时规则要真的落库。

    这是三条路径里最要命的一条：它是整个招聘流程的入口。
    """
    _, link1, _ = two_stage_process
    _rule(link1, name='初筛限时', days=4)

    app = ApplicationService.create_application(
        ApplicationCreateData(candidate_id=candidate.id, position_id=recruiting_position.id)
    )

    assert app.pk is not None
    app = _reload(app)
    assert app.total_time_limit_days == 4, '首阶段限时规则未写入申请'
    assert app.stage_deadline is not None, '有限时规则时 stage_deadline 不得为空'

    record = ApplicationStageRecord.objects.get(application=app, link=link1)
    assert record.total_time_limit_days == 4
    assert record.deadline is not None

    history = ApplicationHistory.objects.get(
        application=app, action=ApplicationHistory.ActionType.CREATED,
    )
    assert history.detail['time_limit_days'] == 4, '创建审计里的限时天数应与规则一致'


def test_create_application_without_rule_falls_back_to_no_deadline(
    two_stage_process, recruiting_position, candidate,
) -> None:
    """没有配规则时走 default 结果，不得报错，也不得凭空造出 deadline。"""
    app = ApplicationService.create_application(
        ApplicationCreateData(candidate_id=candidate.id, position_id=recruiting_position.id)
    )

    assert app.total_time_limit_days == 0
    assert app.stage_deadline is None


def test_create_application_applies_interviewer_extension_shape(
    two_stage_process, recruiting_position, candidate,
) -> None:
    """加时规则存在时，基础值仍以 1 名面试官计（创建阶段不传人数）。"""
    _, link1, _ = two_stage_process
    _rule(link1, name='带加时的初筛', days=3, per_person=2)

    app = ApplicationService.create_application(
        ApplicationCreateData(candidate_id=candidate.id, position_id=recruiting_position.id)
    )

    assert app.total_time_limit_days == 3, \
        '创建阶段按 1 名面试官计，加时不应生效（max(0, 1-1)=0）'


# ============================================================
# 2. advance_application_to_next_stage —— POST .../advance/
# ============================================================
def test_advance_writes_next_stage_time_limit(
    two_stage_process, recruiting_position, candidate, super_user,
) -> None:
    """推进到下一阶段时，限时应换成**下一阶段**的规则值。"""
    _, link1, link2 = two_stage_process
    _rule(link1, name='初筛限时', days=4)
    _rule(link2, name='面试限时', days=10)

    app = ApplicationService.create_application(
        ApplicationCreateData(candidate_id=candidate.id, position_id=recruiting_position.id)
    )
    assert app.total_time_limit_days == 4

    ApplicationService.advance_application_to_next_stage(app, actor=super_user)

    app = _reload(app)
    assert app.current_link_id == link2.id, '应已推进到第二阶段'
    assert app.total_time_limit_days == 10, '推进后限时未换成下一阶段的规则值'

    record = ApplicationStageRecord.objects.get(application=app, link=link2)
    assert record.total_time_limit_days == 10
    assert record.deadline is not None


def test_advance_without_next_stage_rule_clears_deadline(
    two_stage_process, recruiting_position, candidate, super_user,
) -> None:
    """下一阶段没配规则时，deadline 应为空而不是沿用上一阶段。"""
    _, link1, _ = two_stage_process
    _rule(link1, name='初筛限时', days=4)

    app = ApplicationService.create_application(
        ApplicationCreateData(candidate_id=candidate.id, position_id=recruiting_position.id)
    )
    ApplicationService.advance_application_to_next_stage(app, actor=super_user)

    app = _reload(app)
    assert app.total_time_limit_days == 0, '下一阶段无规则时不得沿用上一阶段的限时'


# ============================================================
# 3. jump_application_to_stage —— POST .../jump/
# ============================================================
def test_jump_writes_target_stage_time_limit(
    two_stage_process, recruiting_position, candidate, super_user,
) -> None:
    """跳阶段同样要按**目标阶段**重算限时。"""
    _, link1, link2 = two_stage_process
    _rule(link1, name='初筛限时', days=4)
    _rule(link2, name='面试限时', days=8)

    app = ApplicationService.create_application(
        ApplicationCreateData(candidate_id=candidate.id, position_id=recruiting_position.id)
    )

    ApplicationService.jump_application_to_stage(
        app, target_stage_id=link2.stage_id, actor=super_user,
    )

    app = _reload(app)
    assert app.current_link_id == link2.id
    assert app.total_time_limit_days == 8, '跳转后限时未按目标阶段重算'


# ============================================================
# 4. 兜底：结果对象的字段名本身
# ============================================================
def test_calc_result_field_is_total_lock_days() -> None:
    """``TimeLimitCalcResult`` 没有 total_days —— 12 处误写正源于此。

    这条用例很短，但它是上面那些 AttributeError 的根，
    留着可以让下一个人一眼看清正确字段名。
    """
    from apps.time_limit.services import TimeLimitCalcResult

    fields = {f for f in TimeLimitCalcResult.__dataclass_fields__}
    assert 'total_lock_days' in fields
    assert 'total_days' not in fields, \
        '若哪天真加了 total_days 别名，请同步清理调用方，不要两套名字并存'
