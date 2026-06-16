"""Core AppConfig"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'apps.core'
    verbose_name = '核心模块'

    def ready(self):
        from . import signals  # noqa
