from django.apps import AppConfig


class ProcessConfig(AppConfig):
    name = 'apps.process'
    verbose_name = '招聘流程管理'

    def ready(self):
        from . import signals  # noqa
