from django.apps import AppConfig


class CampusControlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campus_control'
    verbose_name = '校招管控'

    def ready(self):
        from . import signals  # noqa
