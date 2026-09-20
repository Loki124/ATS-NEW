"""Reason Library Django AppConfig."""
from django.apps import AppConfig


class ReasonLibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reason_library'
    verbose_name = '原因库（标签池 + 场景规则）'
