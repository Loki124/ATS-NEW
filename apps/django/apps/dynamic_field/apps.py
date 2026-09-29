from django.apps import AppConfig


class DynamicFieldConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dynamic_field'
    verbose_name = '动态字段定义'

    def ready(self):
        # 注册信号：新增候选人类动态字段时自动生成「对象路径」型指标定义
        from . import signals  # noqa: F401
