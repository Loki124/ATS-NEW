from django.apps import AppConfig


class FieldACLConfig(AppConfig):
    name = 'apps.field_acl'
    verbose_name = '字段级 ACL'

    def ready(self):
        # 2026-08-03 R2: 注册 FieldACL 规则缓存失效信号
        from . import signals  # noqa: F401
