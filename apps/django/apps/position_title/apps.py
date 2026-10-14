"""职务管理 app 配置。"""
from django.apps import AppConfig


class PositionTitleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.position_title'
    verbose_name = '职务管理'
