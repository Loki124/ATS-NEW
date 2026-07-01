"""mou app config - 2026-07-01 stub for permissions-v2 (MOU 业务)"""
from django.apps import AppConfig


class MouConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.mou'
    verbose_name = 'MOU 业务 (大客户协议)'
