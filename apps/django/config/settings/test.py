"""测试环境配置"""
import os

from .base import *  # noqa

DEBUG = True

# 测试环境允许所有 host
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_NAME', str(BASE_DIR / 'dev_db.sqlite3')),
        # 2026-08-04: 改文件 SQLite 代替 :memory:。:memory: 每次 HTTP 请求
        # 用独立连接 → 独立空数据库, 登录和后续 POST 互不可见 → 500。
        # 测试环境(pytest) 用 --reuse-db + :memory: 不受影响。
        'TEST': {
            'NAME': ':memory:',  # pytEST 继续 :memory: 加速
        },
    }
}

# 2026-10-08 (#26): CI 测试库对齐生产 MySQL 8。
#   test-backend job 已起 mysql:8.0 service, 但此前 test settings 写死 SQLite →
#   "CI 绿、生产炸" 风险 (排序规则 / JSON 函数 / 时区等行为差异)。
#   设 DB_ENGINE=mysql 即切到 MySQL; 其余连接参数由 DB_* 环境变量注入
#   (CI 用 mysql service 的 root + 空密码 + 127.0.0.1:3306)。本地快速通道仍默认 SQLite。
if os.environ.get('DB_ENGINE', 'sqlite') == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'ats_test'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {'charset': 'utf8mb4'},
            'TEST': {
                'CHARSET': 'utf8mb4',
                'COLLATION': 'utf8mb4_unicode_ci',
            },
        }
    }

# 关闭密码哈希，加速测试
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# 关闭限流
RATELIMIT_ENABLE = False

# 关掉 DRF throttle, 测试时无限速 (覆盖 base.py 的默认 throttle 配置)
#
# R6 (2026-08-03 寇豆码): 原来这里把 DEFAULT_THROTTLE_RATES 直接清成 {} —— 这是个坑。
#   DEFAULT_THROTTLE_CLASSES 置空只是取消了"全局默认"限流, 但视图上用
#   @throttle_classes([LoginRateThrottle]) 显式声明的限流类照样会被实例化,
#   SimpleRateThrottle.__init__ → get_rate() 在 THROTTLE_RATES 里找不到自己的 scope
#   就会 raise ImproperlyConfigured("No default throttle rate set for 'login' scope"),
#   结果是请求直接 500。也就是说 /api/v1/auth/login、/api/v1/auth/register、
#   /api/v1/auth/change-password 这些带显式 throttle 的端点在测试里根本跑不通。
#
#   正确做法: 保留 base.py 里所有 scope key, 只把配额抬到测试期不可能触达的量级。
#   需要验证限流真实生效的用例, 用 @override_settings 单独把对应 scope 调小。
_TEST_UNLIMITED_RATE = '100000/minute'
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        scope: _TEST_UNLIMITED_RATE
        for scope in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
    },
}

# 关掉 v2 权限 bootstrap (单测中显式调, 见 spec §4.2)
PERMISSION_V2_BOOTSTRAP_DISABLED = True

# 2026-10-08: 关闭权限码集合缓存。否则某个用例跑过 seed_v2_init 后, 缓存里会留下
#   全量 resource_code, 后续用例按 action 派生出 :edit/:delete 并因未授权而 403
#   —— 表现为 batch-screen 等用例**依赖执行顺序**偶发失败。
V2_PERM_CODES_CACHE_TTL = 0

# 更快邮件
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# 关闭迁移以加速
# MIGRATION_MODULES = {app: None for app in LOCAL_APPS}

# 关闭 Celery 异步执行
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# 日志静默
LOGGING['loggers']['apps']['level'] = 'WARNING'

# 2026-08-03 S3: PII 字段加密测试 fallback key
# 测试环境不设 ENCRYPTION_KEY / INTEGRATION_FERNET_KEY, 用固定 dev key 避免启动报错
# ⚠️ 这个 key 不能在生产用, 仅供测试
ENCRYPTION_KEY = 'EgnPPJWZCoGgt-GALcXYPuKhaJHx8s5297wmzS_ykK8='
INTEGRATION_FERNET_KEY = ENCRYPTION_KEY
