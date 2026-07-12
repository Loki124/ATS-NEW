"""测试环境配置"""
from .base import *  # noqa

DEBUG = False

# 测试环境允许所有 host
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# 关闭密码哈希，加速测试
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# 关闭限流
RATELIMIT_ENABLE = False

# 关掉 DRF throttle, 测试时无限速 (覆盖 base.py 的默认 throttle 配置)
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
}

# 关掉 v2 权限 bootstrap (单测中显式调, 见 spec §4.2)
PERMISSION_V2_BOOTSTRAP_DISABLED = True

# 更快邮件
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# 关闭迁移以加速
# MIGRATION_MODULES = {app: None for app in LOCAL_APPS}

# 关闭 Celery 异步执行
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# 日志静默
LOGGING['loggers']['apps']['level'] = 'WARNING'
