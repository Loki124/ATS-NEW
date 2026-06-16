"""轮流邀约服务（PRD v4 §11.4 ROUND_ROBIN 处理规则）

业务场景：
- 阶段为 INVITATION + processing_rule = ROUND_ROBIN
- 处理人池子（如多个 HR），按 Round-Robin 算法轮流分配新邀约
- 抢单机制配合：HR 池子里的人按"上次分配时间"最早的优先

使用场景：
- 当候选人进入邀约阶段时，从池子里挑一个当前最闲的 HR
- 抢单阈值（如 30 分钟）内无人接单 → 重新分配给下一位
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class RoundRobinCandidate:
    """抢单池候选 HR"""
    user_id: str
    last_assigned_at: Optional[str] = None
    current_load: int = 0  # 当前在处理的候选人数
    score: float = 0.0     # 优先级评分（越低越优先）


def pick_round_robin_processor(
    pool_user_ids: List[str],
    last_assignment_map: dict,
    load_map: dict,
) -> Optional[str]:
    """从抢单池中挑选下一位处理人

    策略：先按 last_assigned_at 升序（同时间按 load 升序）

    Args:
        pool_user_ids: HR 池子用户 ID 列表
        last_assignment_map: {user_id: 上次分配时间 (ISO string)}
        load_map: {user_id: 当前在处理候选人数}

    Returns:
        选中的 user_id，若池子为空返回 None
    """
    if not pool_user_ids:
        return None

    # 构造候选
    candidates: List[RoundRobinCandidate] = []
    for uid in pool_user_ids:
        candidates.append(RoundRobinCandidate(
            user_id=uid,
            last_assigned_at=last_assignment_map.get(uid),
            current_load=load_map.get(uid, 0),
        ))

    # 排序：last_assigned_at 升序（None 排前面），再按 load 升序
    def sort_key(c: RoundRobinCandidate):
        # 没分配过的优先，然后按时间从早到晚
        return (
            c.last_assigned_at or '0',  # None 当作最早
            c.current_load,
        )

    candidates.sort(key=sort_key)
    return candidates[0].user_id


def should_reassign(
    current_assignee: str,
    pool_user_ids: List[str],
    assigned_at,
    grab_threshold_minutes: int = 30,
) -> bool:
    """判断是否需要重新分配（抢单超时）

    Args:
        current_assignee: 当前处理人
        pool_user_ids: 池子
        assigned_at: 当前分配时间
        grab_threshold_minutes: 抢单阈值（分钟），默认 30

    Returns:
        是否需要重新分配
    """
    if not assigned_at:
        return True

    elapsed = timezone.now() - assigned_at
    return elapsed > timedelta(minutes=grab_threshold_minutes)


def get_round_robin_status(
    stage_rule,
    current_assignee: Optional[str],
    current_assignee_since: Optional[str],
) -> dict:
    """获取轮流邀约状态（前端展示用）"""
    return {
        'processing_rule': 'ROUND_ROBIN',
        'is_grab_mode': stage_rule.is_grab_mode,
        'grab_threshold': stage_rule.grab_threshold,
        'current_assignee': current_assignee,
        'current_assignee_since': current_assignee_since,
        'processor_order': stage_rule.processor_order or [],
    }
