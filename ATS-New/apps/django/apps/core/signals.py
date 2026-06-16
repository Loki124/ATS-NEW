"""Core Signals

轻量级 signal：监听 last_login 字段变化时同步 last_login_at
（不依赖 django-dirtyfields，使用 Django 内置 get_deferred_fields / pk 判定）
"""
import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import User

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=User)
def sync_last_login_at(sender, instance, **kwargs):
    """Django 内置 last_login 字段被更新时，同步到自定义 last_login_at 字段

    通过对比 instance.pk 是否已存在 + 比较新旧值判断：
    - 新建用户（pk 为空）→ 跳过
    - last_login 变化 → 同步到 last_login_at
    """
    if not instance.pk:
        # 新建用户，跳过
        return
    try:
        old = User.objects.only('last_login').get(pk=instance.pk)
    except User.DoesNotExist:
        return
    if old.last_login != instance.last_login and instance.last_login is not None:
        instance.last_login_at = instance.last_login
        logger.debug('Synced last_login_at for user %s', instance.pk)
