"""设置入口 - 默认生产环境 (fail-safe)

2026-08-03 R3 (寇豆码) 修复:
  原实现 `os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.dev')`,
  且遇到无法识别的模块名会打一行 stderr warning 后**静默回落 dev**。
  而 wsgi.py / asgi.py / Dockerfile / docker-compose 全都用
  `DJANGO_SETTINGS_MODULE=config.settings`(不带后缀) —— 这个值不在白名单里,
  于是生产容器实际跑的是 dev 配置: DEBUG=True + CORS_ALLOW_ALL_ORIGINS=True +
  弱 SECRET_KEY,等于把后台直接敞开。

  修复原则「默认安全 (secure by default)」:
    1. 未设置 DJANGO_SETTINGS_MODULE  → 默认 config.settings.prod
    2. 设置为 config.settings(不带后缀) → 视同 config.settings.prod
    3. 设置为无法识别的值             → 直接 ImproperlyConfigured 抛错,
                                        绝不再静默回落 dev
  本地开发需要 dev 配置时必须显式声明:
    export DJANGO_SETTINGS_MODULE=config.settings.dev
  (manage.py 已为开发者 CLI 显式 setdefault 到 dev,见 manage.py:9)

通过 DJANGO_SETTINGS_MODULE 环境变量切换：
  - config.settings.prod   (默认)
  - config.settings.dev
  - config.settings.test
  - config.settings.base
"""
import os

from django.core.exceptions import ImproperlyConfigured

#: 允许的 settings 模块白名单
_VALID_SETTINGS_MODULES = (
    'config.settings.base',
    'config.settings.dev',
    'config.settings.prod',
    'config.settings.test',
)

#: 未显式指定时的默认值 —— 必须是最严格的 prod
DEFAULT_SETTINGS_MODULE = 'config.settings.prod'

settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '') or DEFAULT_SETTINGS_MODULE

# `config.settings`(包本身,不带环境后缀) 视同生产,而不是 dev
if settings_module == 'config.settings':
    settings_module = DEFAULT_SETTINGS_MODULE

if settings_module not in _VALID_SETTINGS_MODULES:
    raise ImproperlyConfigured(
        'DJANGO_SETTINGS_MODULE=%r 不是合法的配置模块。\n'
        '  合法取值: %s\n'
        '  (R3: 旧实现会静默回落到 dev,导致生产环境跑 DEBUG=True + CORS 全放开,'
        '现已改为直接报错)' % (settings_module, ', '.join(_VALID_SETTINGS_MODULES))
    )

# 重新导出选中的 settings 模块
if settings_module == 'config.settings.base':
    from .base import *  # noqa: F401,F403
elif settings_module == 'config.settings.dev':
    from .dev import *  # noqa: F401,F403
elif settings_module == 'config.settings.prod':
    from .prod import *  # noqa: F401,F403
elif settings_module == 'config.settings.test':
    from .test import *  # noqa: F401,F403
