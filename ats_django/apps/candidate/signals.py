"""Candidate Signals

业务事件：
- 候选人创建/更新 → 写 CandidateHistory（部分通过 service 层显式写入）
- 候选人入库 → 记录原因
"""
import logging
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
    """保存后记录状态变更"""
    if created:
        return  # 创建由 service 层显式记录

    old_state = getattr(instance, '_old_state', None)
    if old_state and old_state != instance.current_state:
        try:
            CandidateHistory.objects.create(
                candidate=instance,
                action='STATE_CHANGED',
                detail={'from': old_state, 'to': instance.current_state},
                operator=getattr(instance, '_updated_by', None),
            )
        except Exception as e:
            logger.warning('Failed to log state change: %s', e)

    old_blacklisted = getattr(instance, '_old_blacklisted', None)
    if old_blacklisted is not None and old_blacklisted != instance.is_blacklisted:
        try:
            CandidateHistory.objects.create(
                candidate=instance,
                action='BLACKLIST_CHANGED',
                detail={'from': old_blacklisted, 'to': instance.is_blacklisted},
                operator=getattr(instance, '_updated_by', None),
            )
        except Exception as e:
            logger.warning('Failed to log blacklist change: %s', e)
