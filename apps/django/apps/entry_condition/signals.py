"""Entry Condition Signals（Phase 3，2026-08-31）

双写镜像到统一规则引擎（best-effort，异常仅记日志，绝不影响 entry_condition 自身事务
与现网行为，见设计文档 §3.3 / §6 Phase 3）：

- EntryConditionRule 保存时 → sync_entry_condition_rule_to_unified
- ConditionItem 保存 / 硬删时 → 重新同步其所属规则（条件内联在 items，规则头 save
  不会携带最新的 items，故 item 变更需反过来重同步父规则）
- EntryConditionLog 保存时 → sync_entry_condition_log_to_unified（评估日志镜像）

双写链路严格可选：仅当 RULE_ENGINE_DOUBLE_WRITE 为真时执行；任何异常都被吞掉并仅记
日志。软删传播由 bridge 在下次 sync 时统一处理（soft_delete() 触发 post_save）。
"""
import logging

from django.conf import settings
from django.db import DatabaseError
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ConditionItem, EntryConditionLog, EntryConditionRule

logger = logging.getLogger(__name__)


def _sync_rule(rule) -> None:
    """best-effort 把一条 EntryConditionRule 镜像到统一规则引擎。"""
    if getattr(settings, 'RULE_ENGINE_DOUBLE_WRITE', False):
        try:
            from apps.rule_engine.bridge import sync_entry_condition_rule_to_unified
            sync_entry_condition_rule_to_unified(rule)
        except (DatabaseError, ValueError, TypeError, AttributeError, OSError):  # 双写失败不得影响现网
            logger.exception(
                'RULE_ENGINE double-write failed for EntryConditionRule %s', rule.id
            )


@receiver(post_save, sender=EntryConditionRule)
def on_rule_saved(sender, instance, created, **kwargs):
    if not kwargs.get('raw'):
        _sync_rule(instance)


@receiver(post_save, sender=ConditionItem)
def on_item_saved(sender, instance, created, **kwargs):
    # 条件项变更 → 重新同步所属规则（conditions 内联在 items，规则头 save 不携带最新 items）
    if not kwargs.get('raw'):
        _sync_rule(instance.rule)


@receiver(post_delete, sender=ConditionItem)
def on_item_deleted(sender, instance, **kwargs):
    # 硬删条件项 → 重新同步所属规则
    try:
        _sync_rule(instance.rule)
    except Exception:  # noqa: BLE001 — 双写失败不得影响现网
        logger.exception(
            'RULE_ENGINE double-write (item delete) failed for rule %s',
            getattr(instance, 'rule_id', '?'),
        )


@receiver(post_save, sender=EntryConditionLog)
def on_log_saved(sender, instance, created, **kwargs):
    # 评估日志 best-effort 镜像到统一执行日志（异常仅记日志）
    if getattr(settings, 'RULE_ENGINE_DOUBLE_WRITE', False) and not kwargs.get('raw'):
        try:
            from apps.rule_engine.bridge import sync_entry_condition_log_to_unified
            sync_entry_condition_log_to_unified(instance)
        except (DatabaseError, ValueError, TypeError, AttributeError, OSError):  # 双写失败不得影响现网
            logger.exception(
                'RULE_ENGINE double-write failed for EntryConditionLog %s', instance.id
            )
