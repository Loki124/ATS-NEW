"""校招专属功能 app 配置（校园大使 / 宣讲会）。"""
from django.apps import AppConfig


class CampusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campus'
    label = 'campus'
    verbose_name = '校招专属功能（校园大使 / 宣讲会）'
