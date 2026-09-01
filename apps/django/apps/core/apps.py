"""Core AppConfig"""
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    name = 'apps.core'
    verbose_name = '核心模块'

    def ready(self):
        from django.conf import settings
        from . import signals  # noqa
        if getattr(settings, 'PERMISSION_V2_BOOTSTRAP_DISABLED', False):
            logger.warning('[bootstrap_v2] PERMISSION_V2_BOOTSTRAP_DISABLED=True, 启动校验被显式关闭')
            return
        # 注意: ready() 在 migrate 等管理命令之前执行, 此时数据库可能尚未建表.
        # bootstrap_permission_v2() 内部会先做存在性探测, 未建表/数据库不可达
        # 时返回 skipped 而非抛错; 只有"表已建但数据缺失"才 raise ImproperlyConfigured.
        from .bootstrap import bootstrap_permission_v2
        result = bootstrap_permission_v2()
        if result.status != 'ok':
            logger.warning('[bootstrap_v2] 启动校验已跳过: %s', result.reason)
