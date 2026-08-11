"""Time Limit Services (PRD v4 §11.5)

- 阶段限时计算：根据候选人特征 + 规则优先级匹配适用规则
- 锁定时长计算：基础锁定时长 + 加时规则 × 人员数
- 抢占式：候选人进入阶段时计算 deadline，写入 ApplicationStageRecord.locked_until
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class TimeLimitCalcResult:
    """限时计算结果"""
    rule_id: Optional[str]
    rule_name: str
    base_lock_days: int
    extension_days: int
    extra_interviewer_days: int
    total_lock_days: int
    effective_scope: str  # ALL / NEW_ONLY
    locked_until: Optional[str] = None  # ISO 8601
    matched: bool = False


def calc_time_limit(
    link,
    candidate,
    interviewer_count: int = 1,
    process_version: str = None,
) -> TimeLimitCalcResult:
    """计算阶段限时

    Args:
        link: ProcessStageLink。**已唯一确定流程版本行**——clone 新版本时
            ProcessStageLink 被深拷贝，每个版本行持有自己独立的一套 link，
            故 ``filter(link=link)`` 本身即完成了版本维度的筛选。
        candidate: Candidate 实例
        interviewer_count: 面试官人数（用于加时计算）
        process_version: **已弃用（deprecated）**，不再参与规则过滤，保留仅为
            向后兼容 API 入参（``time_limit/views.py`` 的 workflow_version）。
            传入值若与 link 所属流程行的 current_version 不一致，会记 warning
            而非静默丢弃——见下方治理说明。

    Returns:
        TimeLimitCalcResult

    治理说明（G2 配套，2026-08-10）—— 原实现的 fail-silent 缺陷：

        原代码为 ``if process_version: rules = rules.filter(workflow_version=process_version)``。
        ``RecruitmentProcess.current_version`` 使用 ``'V1.0'`` 格式，而
        ``Demand/Position.process_version`` 的 default 曾是 ``'1.0'``（无 V 前缀），
        两种格式一旦在调用链上相遇，这个精确字符串比较就静默匹配到**空集**：
        不抛异常、不告警、不留痕迹，时限规则全部失效，表面症状只是"规则配了但从不生效"。

        更严重的是数据面实测（dev 库审计窗口）：现存 23 条 TimeLimitRule 的
        ``workflow_version`` 与 ``process_id`` **全部为空字符串**。这意味着只要调用方
        传入任何非空 process_version，这 23 条规则就一条都匹配不上。

        修复采取"移除冗余过滤"而非"改按 process_id 匹配"：后者看似更严谨，
        但对上述存量数据（``process_id=''``）同样会全量落空，属于把一个 fail-silent
        换成另一个 fail-silent。link 已唯一确定版本行，无需二次确认。
    """
    from .models import TimeLimitRule

    rules = TimeLimitRule.objects.filter(
        link=link,
        enabled=True,
        deleted_at__isnull=True,
    )

    # process_version 不再参与过滤（见上方治理说明）。仅在与 link 实际所属
    # 版本不一致时留下告警痕迹，避免调用方以为自己筛选生效了。
    if process_version:
        actual_version = getattr(link.process, 'current_version', None)
        if actual_version and process_version != actual_version:
            logger.warning(
                'calc_time_limit: 入参 process_version=%r 与 link 所属流程行的 '
                'current_version=%r 不一致；该入参已弃用、不参与过滤，'
                '规则集以 link=%r 为准。（旧实现会在此静默返回空规则集）',
                process_version, actual_version, link.id,
            )

    rules = rules.order_by('priority')

    # 取优先级最高的第一条匹配规则
    for rule in rules:
        if _rule_conditions_match(rule, candidate):
            base = rule.lock_duration
            ext = rule.extension_per_person
            extra = ext * max(0, interviewer_count - 1)
            total = base + extra

            return TimeLimitCalcResult(
                rule_id=rule.id,
                rule_name=rule.rule_name,
                base_lock_days=base,
                extension_days=ext,
                extra_interviewer_days=extra,
                total_lock_days=total,
                effective_scope=rule.effective_scope,
                matched=True,
            )

    return TimeLimitCalcResult(
        rule_id=None,
        rule_name='default',
        base_lock_days=0,
        extension_days=0,
        extra_interviewer_days=0,
        total_lock_days=0,
        effective_scope='NEW_ONLY',
        matched=False,
    )


def _rule_conditions_match(rule, candidate) -> bool:
    """判断规则的 conditions 是否匹配候选人

    rule.conditions 格式（参考 PRD v4 §11.5）：
    [
      {"field": "HIRING_LEVEL", "operator": "IN", "value": ["P5", "P6"]},
      {"field": "URGENCY", "operator": "EQ", "value": "HIGH"}
    ]
    默认 AND 连接
    """
    conditions = rule.conditions or []
    if not conditions:
        return True

    for cond in conditions:
        field = cond.get('field')
        op = cond.get('operator', 'EQ')
        value = cond.get('value')
        actual = _get_candidate_attr(candidate, field)

        if not _compare(op, actual, value):
            return False
    return True


def _get_candidate_attr(candidate, field: str):
    """获取候选人属性"""
    mapping = {
        'CANDIDATE_LEVEL': getattr(candidate, 'level', None),
        'CANDIDATE_SOURCE': getattr(candidate, 'source', None),
        'GENDER': getattr(candidate, 'gender', None),
        'HIGHEST_EDU': getattr(candidate, 'highest_education', None),
        'WORK_YEARS': getattr(candidate, 'work_years', None),
    }
    return mapping.get(field)


def _compare(op: str, actual, expected) -> bool:
    """简化版比较"""
    if op == 'EQ':
        return actual == expected
    if op == 'NEQ':
        return actual != expected
    if op == 'IN':
        return actual in (expected or [])
    if op == 'NOT_IN':
        return actual not in (expected or [])
    if op == 'GT':
        return actual is not None and actual > expected
    if op == 'LT':
        return actual is not None and actual < expected
    if op == 'IS_EMPTY':
        return actual in (None, '', [])
    if op == 'IS_NOT_EMPTY':
        return actual not in (None, '', [])
    return False


def compute_locked_until(base_time, total_lock_days: int):
    """根据基础时间 + 天数计算 locked_until"""
    if not total_lock_days or total_lock_days <= 0:
        return None
    return base_time + timedelta(days=total_lock_days)


def is_time_exceeded(locked_until, now=None) -> bool:
    """判断是否超时"""
    if not locked_until:
        return False
    if now is None:
        now = timezone.now()
    return now > locked_until


def get_remaining_days(locked_until, now=None) -> int:
    """获取剩余天数（向下取整）"""
    if not locked_until:
        return 0
    if now is None:
        now = timezone.now()
    delta = locked_until - now
    return max(0, delta.days)


def get_remaining_hours(locked_until, now=None) -> int:
    """获取剩余小时数"""
    if not locked_until:
        return 0
    if now is None:
        now = timezone.now()
    delta = locked_until - now
    return max(0, int(delta.total_seconds() // 3600))
