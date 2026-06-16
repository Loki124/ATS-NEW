"""Automation Signals

- 规则启用/禁用时清理日志缓存
- 熔断检查
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AutomationRule

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AutomationRule)
def on_rule_saved(sender, instance, created, **kwargs):
    if created:
        logger.info('New automation rule: %s [%s]', instance.name, instance.priority)
