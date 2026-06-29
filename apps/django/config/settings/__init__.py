"""设置入口 - 默认开发环境

通过 DJANGO_SETTINGS_MODULE 环境变量切换：
  - config.settings.dev   (默认)
  - config.settings.prod
  - config.settings.test
"""
import os
import sys

settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

# 简单的健全性检查
if settings_module not in ('config.settings.base', 'config.settings.dev', 'config.settings.prod', 'config.settings.test'):
    print(f"Warning: unknown settings module {settings_module}, falling back to dev", file=sys.stderr)
    settings_module = 'config.settings.dev'

# 重新导出选中的 settings 模块
if settings_module == 'config.settings.base':
    from .base import *  # noqa
elif settings_module == 'config.settings.dev':
    from .dev import *  # noqa
elif settings_module == 'config.settings.prod':
    from .prod import *  # noqa
elif settings_module == 'config.settings.test':
    from .test import *  # noqa
