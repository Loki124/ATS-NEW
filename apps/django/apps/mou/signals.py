"""Mou Signals（Phase 4，2026-09-01）

双写镜像到统一规则引擎（best-effort，异常仅记日志，绝不影响 mou 自身事务与现网行为，
见设计文档 §3.6 / §6 Phase 4）：

- MouRule 保存时 → sync_mou_rule_to_unified
- MouRule 硬删时 → 软删对应的统一 Rule（best-effort），保持双写两侧生命周期一致

双写链路严格可选：仅当 RULE_ENGINE_DOUBLE_WRITE 为真时执行；任何异常都被吞掉并仅记
日志。mou 无独立软删（硬删 + is_active），故「软删传播」由本信号的 post_delete 处理。
"""
import logging

from django.conf import settings
from django.db import DatabaseError
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import MouRule

logger = logging.getLogger(__name__)


def _sync_rule(rule) -> None:
    """best-effort 把一条 MouRule 镜像到统一规则引擎。"""
    if getattr(settings, 'RULE_ENGINE_DOUBLE_WRITE', False):
        try:
            from apps.rule_engine.bridge import sync_mou_rule_to_unified
            sync_mou_rule_to_unified(rule)
        except (DatabaseError, ValueError, TypeError, AttributeError, OSError):  # 双写失败不得影响现网
            logger.exception(
                'RULE_ENGINE double-write failed for MouRule %s', rule.id
            )


def _soft_delete_unified(rule) -> None:
    """MouRule 硬删后，best-effort 软删对应的统一 Rule。"""
    if not getattr(settings, 'RULE_ENGINE_DOUBLE_WRITE', False):
        return
    try:
        from apps.rule_engine.bridge import MOU_SOURCE_APP
        from apps.rule_engine.models import Rule
        unified = Rule.objects.filter(
            source_app=MOU_SOURCE_APP, legacy_id=rule.id,
        ).first()
        if unified and unified.deleted_at is None:
            unified.soft_delete()
    except (DatabaseError, ValueError, TypeError, AttributeError, OSError):  # 双写失败不得影响现网
        logger.exception(
            'RULE_ENGINE double-delete failed for MouRule %s', rule.id
        )


@receiver(post_save, sender=MouRule)
def on_rule_saved(sender, instance, created, **kwargs):
    if not kwargs.get('raw'):
        _sync_rule(instance)


@receiver(post_delete, sender=MouRule)
def on_rule_deleted(sender, instance, **kwargs):
    _soft_delete_unified(instance)
