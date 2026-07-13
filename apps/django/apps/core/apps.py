"""Core AppConfig"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'apps.core'
    verbose_name = '核心模块'

    def ready(self):
        from django.conf import settings
        from . import signals  # noqa
        if not getattr(settings, 'PERMISSION_V2_BOOTSTRAP_DISABLED', False):
            from .bootstrap import bootstrap_permission_v2
            bootstrap_permission_v2()