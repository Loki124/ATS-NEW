"""通用 Apps 配置 - 所有 app 的基类

约定：
- 所有 app 包含 apps.py
- 所有 app 在 models 包中分文件定义模型（避免单文件过长）
- 所有 app 有 __init__.py 暴露 default_app_config
"""
from django.apps import AppConfig


class BaseAppConfig(AppConfig):
    """所有 ATS app 的基类"""
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """应用启动时执行的钩子 - 子类可重写"""
        # 注册 signals
        self._register_signals()

    def _register_signals(self):
        """子类可重写以注册 signals"""
        pass
