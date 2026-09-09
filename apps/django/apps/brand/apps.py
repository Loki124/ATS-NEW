"""品牌信息管理 (G43) app 配置。"""
from django.apps import AppConfig


class BrandConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.brand'
    label = 'brand'
    verbose_name = '品牌信息管理'
