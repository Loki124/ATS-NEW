"""T10 配套：``calc_time_limit`` 的 fail-silent 根除回归（规格 G2）。

这个模块此前**零测试**——这不是巧合，而是缺陷能长期潜伏的原因
=============================================================
原实现里有一行::

    if process_version:
        rules = rules.filter(workflow_version=process_version)

它是精确字符串比较，而系统里的版本号存在**两种格式**：
``RecruitmentProcess.current_version`` 写 ``'V1.0'``，
``Demand/Position.process_version`` 的 default 曾是 ``'1.0'``（无 V 前缀）。
两种格式一旦在调用链上相遇，这个 filter 静默匹配到**空集**：
不抛异常、不告警、不留任何痕迹，所有时限规则失效，
表面症状只是"规则明明配了却从不生效"——没人会把它当 bug 报上来。

dev 库审计窗口（2026-08-10）进一步实测：现存 23 条 ``TimeLimitRule`` 的
``workflow_version`` 与 ``process_id`` **全部为空字符串**。也就是说只要调用方
传入任何非空 process_version，这 23 条规则一条都匹配不上。

修复取"移除冗余过滤"而非"改按 process_id 匹配"：后者对上述存量数据
（``process_id=''``）同样全量落空，只是把一个 fail-silent 换成另一个。
真正的依据是 ``link`` —— clone 新版本时 ``ProcessStageLink`` 被深拷贝，
每个版本行持有自己独立的一套 link，``filter(link=link)`` 本身即完成版本筛选。
这一点由 :func:`test_link_alone_scopes_rules_across_cloned_versions` 钉死。

变异自证（靶心）
================
把 ``time_limit/services.py`` 里那行 filter 加回去，本文件应当出现 **2 红**：

- :func:`test_hits_rule_whose_version_is_blank`   （复刻 dev 库 23 条存量数据）
- :func:`test_hits_rule_across_version_format_dual_track` （复刻 V 前缀双轨）

若加回去仍然全绿，说明这两条用例没有真正卡住缺陷，测试本身失效。
"""
from __future__ import annotations

import logging

import pytest

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
# Seed 工具（dev 库无可用样本，一切自建）
# ============================================================
def make_stage(key: str) -> RecruitmentStage:
    stage, _ = RecruitmentStage.objects.get_or_create(
        code=f'TL{key}',
        defaults={'name': f'限时测试阶段-{key}', 'stage_type': StageType.SCREEN},
    )
    return stage


def make_process(code: str, seq: int, *, is_latest: bool = True) -> RecruitmentProcess:
    return RecruitmentProcess.objects.create(
        code=code,
        name=f'{code} 限时测试流程 V{seq}',
        current_version=f'V{seq}.0',
        version_seq=seq,
        is_latest=is_latest,
        status='ENABLED',
    )


def add_link(process: RecruitmentProcess, stage: RecruitmentStage, order: int) -> ProcessStageLink:
    return ProcessStageLink.objects.create(
        process=process, stage=stage, order=order, is_required=True,
    )


def make_rule(
    link: ProcessStageLink,
    *,
    name: str,
    lock_duration: int = 3,
    workflow_version: str = '',
    process_id: str = '',
    priority: int = 0,
    enabled: bool = True,
    conditions=None,
    extension_per_person: int = 0,
    deleted: bool = False,
) -> TimeLimitRule:
    rule = TimeLimitRule.objects.create(
        link=link,
        process_id=process_id,
        workflow_version=workflow_version,
        rule_name=name,
        conditions=conditions or [],
        lock_duration=lock_duration,
        extension_per_person=extension_per_person,
        priority=priority,
        enabled=enabled,
    )
    if deleted:
        rule.soft_delete()
    return rule


def make_candidate(phone: str, **kwargs) -> Candidate:
    return Candidate.objects.create(name=f'限时候选人-{phone[-4:]}', phone=phone, **kwargs)


# ============================================================
# 1. 靶心：存量数据（workflow_version=''）必须命中
# ============================================================
def test_hits_rule_whose_version_is_blank() -> None:
    """复刻 dev 库 23 条存量规则：workflow_version 为空串。

    调用方传入非空 process_version 时，旧实现 ``filter(workflow_version='V1.0')``
    与 ``''`` 不等 → 空集 → matched=False，且**不报任何错**。
    """
    process = make_process('TLBLANK', 1)
    link = add_link(process, make_stage('BLANK'), 1)
    make_rule(link, name='存量规则', lock_duration=5, workflow_version='')

    result = calc_time_limit(link, make_candidate('13940000001'), process_version='V1.0')

    assert result.matched is True, (
        'workflow_version 为空串的存量规则必须命中——'
        '这正是 fail-silent 缺陷让 dev 库 23 条规则全部失效的场景'
    )
    assert result.rule_name == '存量规则'
    assert result.total_lock_days == 5


# ============================================================
# 2. 靶心：版本号格式双轨必须命中
# ============================================================
def test_hits_rule_across_version_format_dual_track() -> None:
    """规则记的是 'V1.0'，调用方传的是旧格式 '1.0'。

    两者指的是同一个版本，旧实现却因精确字符串比较判定不等 → 空集。
    """
    process = make_process('TLDUAL', 1)
    link = add_link(process, make_stage('DUAL'), 1)
    make_rule(link, name='V前缀规则', lock_duration=7, workflow_version='V1.0')

    result = calc_time_limit(link, make_candidate('13940000002'), process_version='1.0')

    assert result.matched is True, (
        "规则记 'V1.0'、调用方传 '1.0'，指的是同一版本；"
        '旧实现在此静默返回空规则集'
    )
    assert result.total_lock_days == 7


# ============================================================
# 3. link 独占版本维度——移除 version 过滤没有放宽隔离
# ============================================================
def test_link_alone_scopes_rules_across_cloned_versions() -> None:
    """两个版本行各自持有独立 link 与独立规则，彼此不得串。

    这条用例是"移除 workflow_version 过滤"的正当性依据：
    版本隔离由 link 完成，version 字段只是冗余的二次确认。
    """
    stage = make_stage('CLONE')

    v1 = make_process('TLCLONE', 1, is_latest=False)
    v1_link = add_link(v1, stage, 1)
    make_rule(v1_link, name='V1 规则', lock_duration=2, workflow_version='V1.0')

    v2 = make_process('TLCLONE', 2, is_latest=True)
    v2_link = add_link(v2, stage, 1)
    make_rule(v2_link, name='V2 规则', lock_duration=9, workflow_version='V2.0')

    candidate = make_candidate('13940000003')

    r1 = calc_time_limit(v1_link, candidate)
    r2 = calc_time_limit(v2_link, candidate)

    assert r1.rule_name == 'V1 规则' and r1.total_lock_days == 2
    assert r2.rule_name == 'V2 规则' and r2.total_lock_days == 9, (
        '不同版本行的 link 各自独立，规则不得跨版本串用'
    )


def test_rules_of_other_links_never_leak() -> None:
    """同一流程行内的不同阶段 link，规则同样不得互串。"""
    process = make_process('TLLEAK', 1)
    link_a = add_link(process, make_stage('LEAKA'), 1)
    link_b = add_link(process, make_stage('LEAKB'), 2)
    make_rule(link_a, name='A 阶段规则', lock_duration=4)

    result = calc_time_limit(link_b, make_candidate('13940000004'))

    assert result.matched is False, 'B 阶段没有规则，不得借用 A 阶段的'
    assert result.rule_name == 'default'


# ============================================================
# 4. 弃用入参：不一致时留痕，一致时安静
# ============================================================
def test_mismatched_process_version_logs_warning(caplog) -> None:
    """入参与 link 实际所属版本不一致时必须留下告警痕迹。

    旧实现在这里静默返回空集；新实现不再过滤，但也不能一声不吭——
    否则调用方仍以为自己的筛选生效了。
    """
    process = make_process('TLWARN', 3)  # current_version = 'V3.0'
    link = add_link(process, make_stage('WARN'), 1)
    make_rule(link, name='告警规则', lock_duration=1)

    with caplog.at_level(logging.WARNING, logger='apps.time_limit.services'):
        result = calc_time_limit(link, make_candidate('13940000005'), process_version='V1.0')

    assert result.matched is True, '告警归告警，规则该命中还得命中'
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings, '版本不一致必须留下 warning'
    message = warnings[0].getMessage()
    assert 'V1.0' in message and 'V3.0' in message, '告警需同时给出入参值与实际版本'
    assert '弃用' in message, '告警需说明该入参已弃用、不参与过滤'


def test_matching_process_version_is_silent(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger='apps.time_limit.services'):
        process = make_process('TLQUIET', 2)  # 'V2.0'
        link = add_link(process, make_stage('QUIET'), 1)
        make_rule(link, name='安静规则', lock_duration=1)
        calc_time_limit(link, make_candidate('13940000006'), process_version='V2.0')

    assert not [r for r in caplog.records if r.levelno == logging.WARNING], \
        '入参与实际版本一致时不应产生噪音告警'


def test_no_process_version_is_silent(caplog) -> None:
    """主业务路径（application/services）根本不传这个入参，必须零告警。"""
    with caplog.at_level(logging.WARNING, logger='apps.time_limit.services'):
        process = make_process('TLNONE', 1)
        link = add_link(process, make_stage('NONE'), 1)
        make_rule(link, name='默认规则', lock_duration=1)
        result = calc_time_limit(link, make_candidate('13940000007'))

    assert result.matched is True
    assert not [r for r in caplog.records if r.levelno == logging.WARNING]


# ============================================================
# 5. 其余过滤条件不得被顺手放宽
# ============================================================
def test_disabled_rule_is_excluded() -> None:
    process = make_process('TLDIS', 1)
    link = add_link(process, make_stage('DIS'), 1)
    make_rule(link, name='停用规则', lock_duration=8, enabled=False)

    assert calc_time_limit(link, make_candidate('13940000008')).matched is False


def test_soft_deleted_rule_is_excluded() -> None:
    process = make_process('TLDEL', 1)
    link = add_link(process, make_stage('DEL'), 1)
    make_rule(link, name='已删规则', lock_duration=8, deleted=True)

    assert calc_time_limit(link, make_candidate('13940000009')).matched is False


def test_priority_decides_winner() -> None:
    """priority 升序，数字小的先匹配。"""
    process = make_process('TLPRI', 1)
    link = add_link(process, make_stage('PRI'), 1)
    make_rule(link, name='低优先', lock_duration=1, priority=10)
    make_rule(link, name='高优先', lock_duration=6, priority=1)

    result = calc_time_limit(link, make_candidate('13940000010'))

    assert result.rule_name == '高优先'
    assert result.total_lock_days == 6


# ============================================================
# 6. 计算本身
# ============================================================
def test_extension_scales_with_extra_interviewers() -> None:
    process = make_process('TLEXT', 1)
    link = add_link(process, make_stage('EXT'), 1)
    make_rule(link, name='加时规则', lock_duration=3, extension_per_person=2)

    r1 = calc_time_limit(link, make_candidate('13940000011'), interviewer_count=1)
    r3 = calc_time_limit(link, make_candidate('13940000012'), interviewer_count=3)

    assert (r1.base_lock_days, r1.extra_interviewer_days, r1.total_lock_days) == (3, 0, 3)
    assert (r3.base_lock_days, r3.extra_interviewer_days, r3.total_lock_days) == (3, 4, 7), \
        '加时按"超出第一人的人数"计：2 天/人 × 2 人 = 4 天'


def test_zero_or_negative_interviewer_count_never_reduces_lock() -> None:
    process = make_process('TLNEG', 1)
    link = add_link(process, make_stage('NEG'), 1)
    make_rule(link, name='防负规则', lock_duration=3, extension_per_person=2)

    result = calc_time_limit(link, make_candidate('13940000013'), interviewer_count=0)

    assert result.extra_interviewer_days == 0, 'max(0, n-1) 兜底，人数为 0 不得倒扣'
    assert result.total_lock_days == 3


def test_conditions_gate_matching() -> None:
    """conditions 不匹配的规则跳过，继续找下一条。"""
    process = make_process('TLCOND', 1)
    link = add_link(process, make_stage('COND'), 1)
    make_rule(
        link, name='仅硕士', lock_duration=10, priority=1,
        conditions=[{'field': 'HIGHEST_EDU', 'operator': 'EQ', 'value': '硕士'}],
    )
    make_rule(link, name='兜底规则', lock_duration=2, priority=9)

    bachelor = make_candidate('13940000014', highest_education='本科')
    master = make_candidate('13940000015', highest_education='硕士')

    assert calc_time_limit(link, bachelor).rule_name == '兜底规则'
    assert calc_time_limit(link, master).rule_name == '仅硕士'


def test_unmatched_returns_default_result() -> None:
    process = make_process('TLEMPTY', 1)
    link = add_link(process, make_stage('EMPTY'), 1)

    result = calc_time_limit(link, make_candidate('13940000016'))

    assert result.matched is False
    assert result.rule_id is None
    assert result.rule_name == 'default'
    assert result.total_lock_days == 0
    assert result.effective_scope == 'NEW_ONLY'
