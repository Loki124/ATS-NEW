"""顺序邀约服务（PRD v4 §11.4 SEQUENTIAL 处理规则）

业务场景：
- 阶段为 INVITATION（邀约型）+ processing_rule = SEQUENTIAL
- 默认处理人有多个，按 processor_order 顺序处理
- 当前处理人完成（通过/拒绝）后，自动切换到下一位
- 全部处理人都拒绝 → 进入软拒或下阶段处理

输入：
- ApplicationStageRecord（候选人当前阶段记录）
- StageRule（阶段规则）
- ApplicationHistory（决策历史）

输出：
- 更新后的 StageRule.current_processor_index
- 新一轮邀约事件
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class SequentialProcessorInfo:
    """顺序处理人信息"""
    user_id: str
    order: int
    processed: bool = False
    decision: Optional[str] = None  # PASS / FAIL / PENDING
    processed_at: Optional[str] = None


def get_next_sequential_processor(
    processor_order: List[str],
    current_index: int,
    history: List[dict],
) -> Optional[SequentialProcessorInfo]:
    """获取下一位顺序处理人

    Args:
        processor_order: 处理人顺序列表
        current_index: 当前索引
        history: 该阶段历史记录 [{user_id, decision, created_at}]

    Returns:
        下一位处理人信息，若全部处理完返回 None
    """
    if not processor_order:
        return None

    # 构建已处理集合
    processed = {h['user_id']: h['decision'] for h in history}

    # 从 current_index 开始找下一位未处理的
    n = len(processor_order)
    for offset in range(n):
        idx = (current_index + offset) % n
        user_id = processor_order[idx]
        if user_id not in processed:
            return SequentialProcessorInfo(
                user_id=user_id,
                order=idx,
                processed=False,
                decision='PENDING',
            )

    # 全部处理完
    return None


def advance_sequential_processor(
    stage_rule,
    current_user_id: str,
    decision: str,
) -> Optional[str]:
    """推进顺序处理人到下一位

    Args:
        stage_rule: StageRule 实例
        current_user_id: 当前处理人 ID
        decision: 当前处理人的决策 (PASS/FAIL)

    Returns:
        下一位处理人 user_id，若无下一位返回 None
    """
    processor_order: List[str] = stage_rule.processor_order or []
    if not processor_order:
        logger.warning('StageRule %s has empty processor_order', stage_rule.id)
        return None

    # 找到当前处理人位置
    try:
        cur_idx = processor_order.index(current_user_id)
    except ValueError:
        logger.error('Current user %s not in processor_order', current_user_id)
        return None

    # 找到下一位未决策的
    n = len(processor_order)
    for offset in range(1, n + 1):
        next_idx = (cur_idx + offset) % n
        next_user = processor_order[next_idx]
        if next_user != current_user_id:  # 至少推进一位
            stage_rule.current_processor_index = next_idx
            stage_rule.save(update_fields=['current_processor_index', 'updated_at'])
            logger.info(
                'Sequential processor advanced: rule=%s, %s -> %s',
                stage_rule.id, current_user_id, next_user,
            )
            return next_user

    # 已环绕一周
    return None


def is_sequential_complete(processor_order: List[str], history: List[dict]) -> bool:
    """判断顺序处理是否已全部完成"""
    if not processor_order:
        return False
    processed_users = {h['user_id'] for h in history}
    return all(u in processed_users for u in processor_order)


def get_sequential_status(stage_rule, history: List[dict]) -> dict:
    """获取顺序处理状态（用于前端展示）"""
    processor_order: List[str] = stage_rule.processor_order or []
    history_by_user = {h['user_id']: h for h in history}

    processors = []
    for idx, uid in enumerate(processor_order):
        h = history_by_user.get(uid)
        processors.append({
            'user_id': uid,
            'order': idx,
            'is_current': idx == stage_rule.current_processor_index,
            'decision': h.get('decision') if h else 'PENDING',
            'processed_at': h.get('created_at') if h else None,
        })

    return {
        'processing_rule': 'SEQUENTIAL',
        'current_index': stage_rule.current_processor_index,
        'processors': processors,
        'is_complete': is_sequential_complete(processor_order, history),
    }


@transaction.atomic
def reset_sequential_processor(stage_rule):
    """重置顺序处理（阶段重启时使用）"""
    stage_rule.current_processor_index = 0
    stage_rule.save(update_fields=['current_processor_index', 'updated_at'])
