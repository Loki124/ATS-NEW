from django.apps import AppConfig


class CandidateConfig(AppConfig):
    name = 'apps.candidate'
    verbose_name = '候选人'

    def ready(self):
        from . import signals  # noqa
