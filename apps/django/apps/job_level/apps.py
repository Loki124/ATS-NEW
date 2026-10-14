"""职级管理 app 配置。"""
from django.apps import AppConfig


class JobLevelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.job_level'
    verbose_name = '职级管理'
