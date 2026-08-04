"""Resume Flow AppConfig"""
from django.apps import AppConfig


class ResumeFlowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.resume_flow'
    verbose_name = '审批流'
