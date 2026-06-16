"""开发环境配置

DATABASES 不再覆盖 base.py 的配置 - 由 DATABASE_URL 决定（MySQL/PostgreSQL/SQLite）
如需强制 SQLite：.env 中设 DATABASE_URL=sqlite:///db.sqlite3
"""
from .base import *  # noqa
from .base import INSTALLED_APPS, MIDDLEWARE

DEBUG = True
INTERNAL_IPS = ['127.0.0.1']

# 关闭限流
RATELIMIT_ENABLE = False

# CORS 允许所有（仅开发）
CORS_ALLOW_ALL_ORIGINS = True

# 关闭 CSRF（仅开发，配合 DRF Token 认证）
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# 邮件
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 日志 - 安全写入避免 KeyError
LOGGING['loggers'].setdefault('django.db.backends', {
    'handlers': ['console'], 'level': 'DEBUG', 'propagate': False,
})['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'

# 启用 Django Debug Toolbar（仅当已安装时）
try:
    import debug_toolbar  # noqa
    if 'debug_toolbar' not in INSTALLED_APPS:
        INSTALLED_APPS = INSTALLED_APPS + ['debug_toolbar']
        MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
except ImportError:
    pass
