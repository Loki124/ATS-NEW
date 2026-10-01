"""Time Limit Signals（Phase 3，2026-08-31）

双写镜像到统一规则引擎（best-effort，异常仅记日志，绝不影响 time_limit 自身事务与现网
行为，见设计文档 §3.4 / §6 Phase 3）：

- TimeLimitRule 保存时 → sync_time_limit_rule_to_unified

time_limit 的条件内联在 TimeLimitRule.conditions（JSON），随规则头 save 一起落库，故
只需在规则上挂信号即可；软删由 SoftDeleteViewSetMixin 调用 soft_delete()（触发
post_save），bridge 在下次 sync 时统一传播到统一侧。
"""
from django.db import DatabaseError
import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import TimeLimitRule

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TimeLimitRule)
def on_rule_saved(sender, instance, created, **kwargs):
    if getattr(settings, 'RULE_ENGINE_DOUBLE_WRITE', False) and not kwargs.get('raw'):
        try:
            from apps.rule_engine.bridge import sync_time_limit_rule_to_unified
            sync_time_limit_rule_to_unified(instance)
        except (DatabaseError, ValueError, TypeError, AttributeError, OSError):  # 双写失败不得影响现网
            logger.exception(
                'RULE_ENGINE double-write failed for TimeLimitRule %s', instance.id
            )
