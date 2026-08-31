from django.apps import AppConfig


class EntryConditionConfig(AppConfig):
    name = 'apps.entry_condition'
    verbose_name = '进入条件规则'

    def ready(self):
        from . import signals  # noqa
