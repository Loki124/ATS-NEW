"""测试环境配置"""
from .base import *  # noqa

DEBUG = False

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

# 更快邮件
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# 关闭迁移以加速
# MIGRATION_MODULES = {app: None for app in LOCAL_APPS}

# 关闭 Celery 异步执行
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# 日志静默
LOGGING['loggers']['apps']['level'] = 'WARNING'
