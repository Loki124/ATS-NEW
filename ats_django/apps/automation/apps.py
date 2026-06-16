from django.apps import AppConfig


class AutomationConfig(AppConfig):
    name = 'apps.automation'
    verbose_name = '自动化规则'

    def ready(self):
        from . import signals  # noqa
