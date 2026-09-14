"""码表库 app 配置。"""
from django.apps import AppConfig


class CodeTableConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.code_table'
    verbose_name = '码表库'
