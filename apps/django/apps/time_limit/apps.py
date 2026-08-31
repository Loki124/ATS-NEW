from django.apps import AppConfig


class TimeLimitConfig(AppConfig):
    name = 'apps.time_limit'
    verbose_name = '阶段限时规则'

    def ready(self):
        from . import signals  # noqa
