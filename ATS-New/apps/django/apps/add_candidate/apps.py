"""Django App Config for add_candidate"""
from django.apps import AppConfig


class AddCandidateConfig(AppConfig):
    name = 'apps.add_candidate'
    verbose_name = '候选人创建（V2）'

    def ready(self):
        # Phase 2 会在此注册 signals
        pass
