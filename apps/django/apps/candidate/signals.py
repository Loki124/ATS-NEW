"""Candidate Signals

业务事件：
- 候选人创建/更新 → 写 CandidateHistory（首选由 service 层显式写入，带 actor）
- 本 signal 退化为兜底：当 service 没显式记录时才记录（admin / .update() 旁路 /
  迁移脚本 / 测试直连模型），此时 created_by 可为 None（NULL 表示"自动信号、
  不可溯源"）。

2026-08-03 BUG-6 修复：原先 post_save 里读 getattr(instance, '_updated_by', None)
永远拿到 None（全仓无 _updated_by 赋值点），导致 STATE_CHANGED / BLACKLIST_CHANGED
两条自动审计 created_by=None，无法溯源。改为：
- service 层在调用 save() 前显式写 CandidateHistory(action='STATE_CHANGED' / 'BLACKLIST_CHANGED', created_by=actor) 并设 instance._state_change_recorded / _blacklist_change_recorded = True
- 本 signal 仅当对应标志未置位时才补写兜底记录, created_by=None 表示"非业务路径触发的变更"
"""
import logging

from django.db import IntegrityError, OperationalError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Candidate, CandidateHistory

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Candidate)
def capture_old_state(sender, instance, **kwargs):
    """保存前捕获旧状态"""
    if instance.pk:
        try:
            old = Candidate.objects.get(pk=instance.pk)
            instance._old_state = old.current_state
            instance._old_tags = list(old.tags or [])
            instance._old_blacklisted = old.is_blacklisted
        except Candidate.DoesNotExist:
            pass


@receiver(post_save, sender=Candidate)
def log_state_change(sender, instance, created, **kwargs):
    """保存后记录状态 / 黑名单变更的兜底审计。

    设计：
    - 创建 (created=True) 不写, 由 service.create_candidate 显式写 CREATED
    - 状态变更: 若 service 已写 (instance._state_change_recorded=True), 跳过; 否则兜底写一行 STATE_CHANGED, created_by=None
    - 黑名单变更: 同上, 用 _blacklist_change_recorded 标志
    - created_by 为 None 在此处是合法值, NULL = "非业务路径自动审计", 不可溯源但不抛错
    """
    if created:
        return

    old_state = getattr(instance, '_old_state', None)
    state_recorded = getattr(instance, '_state_change_recorded', False)
    if old_state and old_state != instance.current_state and not state_recorded:
        try:
            CandidateHistory.objects.create(
                candidate=instance,
                action='STATE_CHANGED',
                detail={'from': old_state, 'to': instance.current_state},
                created_by=None,  # 兜底场景, NULL 表示不可溯源
            )
        except (OperationalError, IntegrityError, ValueError) as e:  # post_save signal 兜底审计, 审计失败不应阻断主流程 (fallback 路径)
            logger.warning('Failed to log state change (fallback): %s', e)

    old_blacklisted = getattr(instance, '_old_blacklisted', None)
    blacklist_recorded = getattr(instance, '_blacklist_change_recorded', False)
    if old_blacklisted is not None and old_blacklisted != instance.is_blacklisted and not blacklist_recorded:
        try:
            CandidateHistory.objects.create(
                candidate=instance,
                action='BLACKLIST_CHANGED',
                detail={'from': old_blacklisted, 'to': instance.is_blacklisted},
                created_by=None,  # 兜底场景
            )
        except (OperationalError, IntegrityError, ValueError) as e:  # post_save signal 兜底审计, 审计失败不应阻断主流程 (fallback 路径)
            logger.warning('Failed to log blacklist change (fallback): %s', e)
