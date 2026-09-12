from django.apps import AppConfig


class DuplicateRuleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.duplicate_rule'
    verbose_name = '重复候选人规则'
