"""Automation Signals

- 规则启用/禁用时清理日志缓存
- 熔断检查
- Phase 2（2026-08-31）：automation 记录保存/软删时，best-effort 双写到统一规则引擎。
  双写链路严格可选与幂等：仅当 RULE_ENGINE_DOUBLE_WRITE 为真时执行；任何异常都被
  吞掉并仅记日志，绝不影响 automation 自身的事务与现网行为（见设计文档 §3.2）。
"""
import logging

from django.db import IntegrityError, OperationalError
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AutomationLog, AutomationRule

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AutomationRule)
def on_rule_saved(sender, instance, created, **kwargs):
    if created:
        logger.info('New automation rule: %s [%s]', instance.name, instance.priority)

    # Phase 2：双写镜像到统一规则引擎（best-effort，异常仅记日志）
    if getattr(settings, 'RULE_ENGINE_DOUBLE_WRITE', False) and not kwargs.get('raw'):
        try:
            from apps.rule_engine.bridge import sync_automation_rule_to_unified
            sync_automation_rule_to_unified(instance)
        except (OperationalError, IntegrityError, ValueError):  # 双写失败不得影响现网
            logger.exception(
                'RULE_ENGINE double-write failed for AutomationRule %s', instance.id
            )


@receiver(post_save, sender=AutomationLog)
def on_log_saved(sender, instance, created, **kwargs):
    # Phase 2：执行日志 best-effort 镜像到统一执行日志（异常仅记日志）
    if getattr(settings, 'RULE_ENGINE_DOUBLE_WRITE', False) and not kwargs.get('raw'):
        try:
            from apps.rule_engine.bridge import sync_automation_log_to_unified
            sync_automation_log_to_unified(instance)
        except (OperationalError, IntegrityError, ValueError):  # 双写失败不得影响现网
            logger.exception(
                'RULE_ENGINE double-write failed for AutomationLog %s', instance.id
            )
