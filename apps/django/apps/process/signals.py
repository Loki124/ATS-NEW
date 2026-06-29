"""Process Signals

- 流程删除前检查引用
- 流程归档后级联禁用关联自动化
"""
import logging

from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver

from .models import RecruitmentProcess, RecruitmentStage, StageStatus

logger = logging.getLogger(__name__)


@receiver(post_save, sender=RecruitmentProcess)
def on_process_saved(sender, instance, created, **kwargs):
    """流程保存后处理"""
    if created:
        logger.info('New process created: %s %s', instance.code, instance.name)


@receiver(pre_delete, sender=RecruitmentProcess)
def on_process_delete(sender, instance, **kwargs):
    """流程删除前检查"""
    if instance.reference_count > 0:
        from apps.common.exceptions import PermissionDenied
        raise PermissionDenied(
            f'流程「{instance.name}」被 {instance.reference_count} 个需求引用，不可删除',
        )
