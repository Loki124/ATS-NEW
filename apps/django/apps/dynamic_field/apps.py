from django.apps import AppConfig


class DynamicFieldConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dynamic_field'
    verbose_name = '动态字段定义'
