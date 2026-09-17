"""Data Permission app config."""
from django.apps import AppConfig


class DataPermissionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_permission'
    label = 'data_permission'
    verbose_name = '字段权限'
