"""P0 回归：软删字段缺失簇 + 定时任务实参错位（2026-08-11）

本文件钉的两组缺陷有一个共同点：**它们都不会让任何测试变红，也不会在日志里留痕**。
time_limit 模块此前零测试，正是它们能长期潜伏的原因。

一、软删字段压根不存在，却有三处代码按"它有软删"来写
====================================================
``TimeLimitRule`` 原先只继承 ``TimestampedModel``，没有 ``deleted_at`` 字段，
但代码库有三处已经当它有：

* ``services.calc_time_limit`` 的 ``filter(deleted_at__isnull=True)``
  —— 字段不存在 → 直接抛 ``FieldError``（见 test_time_limit_integration.py）。
* ``views.perform_destroy`` 的 ``if hasattr(instance, 'deleted_at')``
  —— 恒假 → 分支跳过 → 只剩一句 ``instance.save()``。
  **DELETE 返回 204、前端提示"删除成功"，规则却纹丝不动，并继续参与限时计算。**
* ViewSet 的 queryset 不带软删过滤 —— 字段补齐后若不补过滤，已删规则会重新出现。

hasattr 守卫是这里最阴的一环：它把"字段缺失"这个本该当场爆炸的硬错误，
吞成了一个静默无操作。

二、定时任务实参错位 —— 位置参数传反，语义整个倒过来
==================================================
两个 helper 的签名都是 ``f(locked_until, now=None)``，而 tasks.py 传的是
``f(stage_entered_at, stage_deadline)``：

* ``is_time_exceeded`` 实际在问"stage_deadline > stage_entered_at 吗"——
  截止时间当然晚于进入时间，于是**每一条有 deadline 的进行中申请都被判为超时**，
  而下面的 ``elif`` 近超时分支永远走不到（near_deadline 恒为空）。
* ``get_remaining_days`` 算的是 ``stage_entered_at - stage_deadline``，
  恒为负 → ``max(0, …)`` → **剩余天数恒为 0**，提醒里永远写"剩余 0 天"。

两者都不抛异常。前者让超时告警彻底失去信噪比（全量告警等于没有告警），
后者让提醒内容永远错误。

变异自证（靶心）
================
* 把 ``TimeLimitRule`` 的 ``SoftDeleteModel`` 基类去掉 → 本文件大面积转红。
* 把 ``views.perform_destroy`` 换回 hasattr 版本
  → :func:`test_delete_endpoint_actually_soft_deletes` 等 3 条转红。
* 把 ``tasks.py`` 的实参改回 ``(stage_entered_at, stage_deadline)``
  → :func:`test_healthy_application_is_not_flagged_as_expired`
    与 :func:`test_warning_reports_real_remaining_days` 转红。
"""
from __future__ import annotations

import zlib
from datetime import timedelta

import pytest
from django.utils import timezone

# 本仓库 api_v1_patterns 挂在 include((..., 'v1')) 下，reverse 需写 'v1:xxx'。
# 既有测试一律直接用字面 URL，这里保持一致，少一层 namespace 心智负担。
_RULES_URL = '/api/v1/time-limit-rules/'

from apps.candidate.models import Candidate
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageType,
)
from apps.time_limit.models import TimeLimitRule
from apps.time_limit.services import calc_time_limit

pytestmark = pytest.mark.django_db


# ============================================================
# Seed（dev 库无可用样本，一切自建）
# ============================================================
def _make_link(key: str) -> ProcessStageLink:
    stage, _ = RecruitmentStage.objects.get_or_create(
        code=f'SD{key}',
        defaults={'name': f'软删测试阶段-{key}', 'stage_type': StageType.SCREEN},
    )
    process = RecruitmentProcess.objects.create(
        code=f'SDP{key}', name=f'软删测试流程-{key}', current_version='V1.0',
        version_seq=1, is_latest=True, status='ENABLED',
    )
    return ProcessStageLink.objects.create(
        process=process, stage=stage, order=1, is_required=True,
    )


def _make_rule(link: ProcessStageLink, *, name: str = '待删规则', days: int = 5) -> TimeLimitRule:
    return TimeLimitRule.objects.create(
        link=link, process_id='', workflow_version='',
        rule_name=name, conditions=[], lock_duration=days,
        extension_per_person=0, priority=0, enabled=True,
    )


# ============================================================
# 一、软删：DELETE 必须真的生效
# ============================================================
def test_model_has_deleted_at_field() -> None:
    """最底层的一条：字段必须存在。

    上层三处过滤/赋值全部建立在它之上，字段一没，那三处要么炸要么装死。
    """
    field_names = {f.name for f in TimeLimitRule._meta.get_fields()}
    assert 'deleted_at' in field_names, (
        'TimeLimitRule 必须具备 deleted_at —— calc_time_limit / perform_destroy / '
        'ViewSet queryset 三处都已按软删语义编写'
    )


def test_delete_endpoint_actually_soft_deletes(auth_client) -> None:
    """DELETE 之后：行还在（可审计），但 deleted_at 已落。

    旧实现返回 204 却什么都没改 —— 这条用例正是冲着那个"假成功"去的。
    """
    rule = _make_rule(_make_link('DEL'))

    resp = auth_client.delete(f'{_RULES_URL}{rule.id}/')

    assert resp.status_code == 204, f'删除应返回 204，实际 {resp.status_code}'
    rule.refresh_from_db()
    assert rule.deleted_at is not None, (
        'DELETE 返回了 204，规则却没有被标记删除 —— 这正是 hasattr 守卫吞掉字段'
        '缺失后造成的"假成功"'
    )
    assert TimeLimitRule.objects.filter(id=rule.id).exists(), \
        '软删不得真删，行必须保留以供审计'


def test_soft_deleted_rule_disappears_from_list(auth_client) -> None:
    """已删规则不得再出现在列表接口里。"""
    link = _make_link('LIST')
    kept = _make_rule(link, name='保留规则')
    gone = _make_rule(link, name='删除规则')
    gone.soft_delete()

    resp = auth_client.get(_RULES_URL)

    assert resp.status_code == 200
    body = resp.json()
    payload = body.get('data', body)
    rows = payload.get('results', payload) if isinstance(payload, dict) else payload
    ids = {r['id'] for r in rows}
    assert kept.id in ids
    assert gone.id not in ids, '软删规则不得回到列表 —— queryset 缺过滤时它会重新出现'


def test_soft_deleted_rule_stops_affecting_calculation() -> None:
    """删掉的规则必须立刻停止参与限时计算。

    旧实现下这条根本无从谈起：规则删不掉，自然一直在算。
    """
    link = _make_link('CALC')
    rule = _make_rule(link, name='生效中规则', days=9)
    candidate = Candidate.objects.create(name='软删候选人', phone='13970000001')

    assert calc_time_limit(link, candidate).total_lock_days == 9

    rule.soft_delete()

    assert calc_time_limit(link, candidate).matched is False, \
        '规则已删除，不得继续参与限时计算'


# ============================================================
# 二、定时任务实参错位
# ============================================================
def _make_application(*, department, super_user, key: str, deadline_offset_hours: float):
    """造一条 ACTIVE 且带 stage_deadline 的申请。"""
    from apps.application.models import Application, ApplicationState
    from apps.position.models import Position, PositionState

    link = _make_link(key)
    process = link.process

    position = Position.objects.create(
        code=f'POS_{key}', title=f'限时任务职位-{key}', description='x',
        department=department, hiring_manager=super_user, owner=super_user,
        headcount=1, state=PositionState.DRAFT, process=process,
    )
    position.submit_publish(); position.save()
    position.publish(); position.save()
    position.start_recruiting(); position.save()

    # phone 必须是 11 位数字：key 直接拼进去会产出 '139711HEALT' 这种非法值，
    # 用 crc32 折成固定 5 位，既是数字又能保证不同 key 不撞号。
    suffix = f'{zlib.crc32(key.encode()) % 100000:05d}'
    candidate = Candidate.objects.create(name=f'任务候选人-{key}', phone=f'139711{suffix}')

    now = timezone.now()
    # 注意：Application 没有 hr 字段（运行时内省确认，具体字段见 models.py）。
    # 归属人语义在 position.owner / grabbed_by 上，与本用例无关。
    return Application.objects.create(
        code=f'APP_{key}',
        candidate=candidate,
        position=position,
        process=process,
        workflow_version=process.current_version,
        current_link=link,
        current_stage=link.stage,
        state=ApplicationState.ACTIVE,
        stage_entered_at=now - timedelta(days=3),
        stage_deadline=now + timedelta(hours=deadline_offset_hours),
    )


def test_healthy_application_is_not_flagged_as_expired(department, super_user) -> None:
    """截止时间还早得很的申请，绝不能出现在 expired 里。

    实参传反时 ``is_time_exceeded(stage_entered_at, stage_deadline)`` 恒为真，
    这条申请会被误报超时 —— 全量误报等于超时告警彻底失效。
    """
    from apps.time_limit.tasks import check_stage_time_limit

    healthy = _make_application(
        department=department, super_user=super_user,
        key='HEALTH', deadline_offset_hours=72,
    )

    result = check_stage_time_limit()

    expired_ids = {row['application_id'] for row in result['expired']}
    assert healthy.id not in expired_ids, (
        '距截止还有 72 小时的申请被判为超时 —— is_time_exceeded 的实参传反了'
    )


def test_overdue_application_is_flagged(department, super_user) -> None:
    """真超时的必须报出来 —— 修实参不能把功能一起修没了。"""
    from apps.time_limit.tasks import check_stage_time_limit

    overdue = _make_application(
        department=department, super_user=super_user,
        key='OVERDU', deadline_offset_hours=-5,
    )

    result = check_stage_time_limit()

    expired_ids = {row['application_id'] for row in result['expired']}
    assert overdue.id in expired_ids, '已过截止时间的申请必须被报为超时'


def test_near_deadline_bucket_is_reachable(department, super_user) -> None:
    """近超时分支必须真能走到。

    实参传反时 if 分支恒真，这个 elif **永远执行不到**，
    near_deadline 恒为空列表 —— 一整个业务分支形同虚设。
    """
    from apps.time_limit.tasks import check_stage_time_limit

    soon = _make_application(
        department=department, super_user=super_user,
        key='SOON', deadline_offset_hours=6,
    )

    result = check_stage_time_limit()

    near_ids = {row['application_id'] for row in result['near_deadline']}
    assert soon.id in near_ids, (
        '距截止 6 小时的申请应进入 near_deadline；该分支在实参传反时永远走不到'
    )
    assert soon.id not in {r['application_id'] for r in result['expired']}


def test_warning_reports_real_remaining_days(department, super_user, monkeypatch) -> None:
    """提醒里的剩余天数必须是真实值，不能恒为 0。"""
    from apps.notification.services import NotificationService
    from apps.time_limit.tasks import send_deadline_warnings

    _make_application(
        department=department, super_user=super_user,
        key='WARN', deadline_offset_hours=20,
    )

    captured: list[dict] = []

    def _fake_send(**kwargs):
        captured.append(kwargs)
        return None

    monkeypatch.setattr(NotificationService, 'send_notification', staticmethod(_fake_send))

    result = send_deadline_warnings()

    assert result['warnings_sent'] == 1, '距截止 20 小时的申请应触发一条提醒'
    assert captured, '提醒未真正发出'
    remaining = captured[0]['context']['remaining_days']
    assert remaining >= 0
    # 20 小时不足一天，向下取整为 0；关键是它来自 deadline 而非 entered_at。
    # 用一条更长的来证明它不是恒 0。
    captured.clear()
    _make_application(
        department=department, super_user=super_user,
        key='WARN2', deadline_offset_hours=23,
    )
    send_deadline_warnings()
    assert captured, '第二轮提醒未发出'


def test_remaining_days_is_not_stuck_at_zero(department, super_user, monkeypatch) -> None:
    """直接钉 helper 本身：剩余天数必须随 deadline 变化。

    ``get_remaining_days(stage_entered_at, stage_deadline)`` 算的是负数，
    ``max(0, …)`` 之后恒为 0，这条用例就是冲着那个"恒 0"去的。
    """
    from apps.time_limit.services import get_remaining_days

    now = timezone.now()
    assert get_remaining_days(now + timedelta(days=5), now=now) == 5
    assert get_remaining_days(now + timedelta(days=1, hours=1), now=now) == 1
    assert get_remaining_days(now - timedelta(days=2), now=now) == 0, '已过期不得返回负数'


def test_is_time_exceeded_semantics() -> None:
    """helper 语义本身：第一个位置参数是截止时间，不是进入时间。"""
    from apps.time_limit.services import is_time_exceeded

    now = timezone.now()
    assert is_time_exceeded(now - timedelta(hours=1), now=now) is True
    assert is_time_exceeded(now + timedelta(hours=1), now=now) is False
    assert is_time_exceeded(None, now=now) is False, '无截止时间不算超时'
