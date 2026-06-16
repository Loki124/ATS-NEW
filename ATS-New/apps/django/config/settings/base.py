"""
Django settings for ATS Recruitment Management System.

生产环境请使用 config.settings.prod
开发环境使用 config.settings.dev
测试环境使用 config.settings.test
"""

from pathlib import Path
from datetime import timedelta
import os

# 优先用 PyMySQL 模拟 mysqlclient（避免 C 扩展系统依赖）
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

import environ

# 探测可选依赖
try:
    from pythonjsonlogger import jsonlogger  # noqa: F401
    _HAS_JSON_LOGGER = True
except ImportError:
    _HAS_JSON_LOGGER = False

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CORS_ALLOWED_ORIGINS=(list, []),
    PROMETHEUS_ENABLED=(bool, False),
    LOG_LEVEL=(str, 'INFO'),
)

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 读取 .env
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))

# 读取 .env.example（仅作为后备）
env_example = BASE_DIR / '.env.example'
if env_example.exists() and not env_file.exists():
    environ.Env.read_env(str(env_example))

# === 安全 ===
SECRET_KEY = env('DJANGO_SECRET_KEY', default='insecure-dev-key-change-me')
DEBUG = env('DJANGO_DEBUG')
ALLOWED_HOSTS = env('DJANGO_ALLOWED_HOSTS')

# === 应用 ===
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django_celery_beat',
    'django_celery_results',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    'django_extensions',
    'channels',
    'django_prometheus',
]

LOCAL_APPS = [
    # 核心
    'apps.core',
    'apps.field_acl',
    'apps.audit',
    'apps.notification',
    'apps.gdpr',
    'apps.integration',
    'apps.common',
    # 流程域
    'apps.process',
    'apps.entry_condition',
    'apps.time_limit',
    'apps.automation',
    # 业务域
    'apps.candidate',
    'apps.application',
    'apps.demand',
    'apps.position',
    'apps.offer',
    'apps.onboarding',
    'apps.invitation',
    'apps.interview',
    'apps.referral',
    'apps.talent_pool',
    'apps.channel',
    'apps.analytics',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# === 中间件 ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 自定义
    'apps.core.middleware.RequestIdMiddleware',
    'apps.audit.middleware.AuditMiddleware',
]

if env('PROMETHEUS_ENABLED'):
    MIDDLEWARE.insert(0, 'django_prometheus.middleware.PrometheusBeforeMiddleware')
    MIDDLEWARE.append('django_prometheus.middleware.PrometheusAfterMiddleware')

# === 根 URL ===
ROOT_URLCONF = 'config.urls'

# === 模板 ===
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'ats_django' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# === WSGI / ASGI ===
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# === 数据库 ===
# 优先级：MySQL > PostgreSQL > SQLite
# 通过 DATABASE_URL 前缀识别（mysql://, postgres://, sqlite:///）
DATABASE_URL = env('DATABASE_URL', default='sqlite:///db.sqlite3')

if DATABASE_URL.startswith('mysql'):
    # MySQL 配置（生产推荐）
    DATABASES = {
        'default': env.db(
            'DATABASE_URL',
            default='mysql://ats_user:ats_password@localhost:3306/ats_db',
        ),
    }
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS'].update({
        'charset': 'utf8mb4',
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
    })
elif DATABASE_URL.startswith('postgres'):
    DATABASES = {
        'default': env.db('DATABASE_URL'),
    }
else:
    # SQLite - 仅用于本地开发/测试
    # 解析 sqlite:/// 后的路径（支持绝对和相对）
    if DATABASE_URL.startswith('sqlite:////'):
        # sqlite:////abs/path → 绝对路径
        db_name = DATABASE_URL[len('sqlite:///'):]
    elif DATABASE_URL.startswith('sqlite:///'):
        # sqlite:///rel/path → 相对 BASE_DIR
        db_name = str(BASE_DIR / DATABASE_URL[len('sqlite:///'):])
    else:
        db_name = str(BASE_DIR / 'db.sqlite3')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_name,
        }
    }

# === 密码校验 ===
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# === 国际化 ===
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# === 静态文件 ===
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# === 媒体文件 ===
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# === 日志目录 ===
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# === 自定义用户模型 ===
AUTH_USER_MODEL = 'core.User'

# === DRF 配置 ===
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '1000/minute',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

# === JWT 配置 ===
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# === CORS ===
CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['X-Request-Id', 'X-Total-Count']

# === Spectacular (OpenAPI) ===
SPECTACULAR_SETTINGS = {
    'TITLE': 'ATS Recruitment API',
    'DESCRIPTION': '招聘管理系统 RESTful API',
    'VERSION': '4.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/v1',
    'TAGS': [
        {'name': 'auth', 'description': '认证'},
        {'name': 'stages', 'description': '阶段'},
        {'name': 'processes', 'description': '招聘流程'},
        {'name': 'entry-conditions', 'description': '进入条件规则'},
        {'name': 'time-limits', 'description': '阶段限时规则'},
        {'name': 'automation', 'description': '自动化规则'},
        {'name': 'candidates', 'description': '候选人'},
        {'name': 'applications', 'description': '申请'},
        {'name': 'demands', 'description': '需求'},
        {'name': 'positions', 'description': '职位'},
        {'name': 'offers', 'description': 'Offer'},
        {'name': 'onboardings', 'description': '入职'},
        {'name': 'talent-pool', 'description': '人才库'},
        {'name': 'analytics', 'description': '数据中心'},
        {'name': 'notifications', 'description': '通知'},
        {'name': 'audit', 'description': '审计'},
        {'name': 'gdpr', 'description': 'GDPR'},
    ],
}

# === Redis & 缓存 ===
# 注：django-redis 5.4.x 的 RedisCacheClient 与 redis 5.x 不兼容 (CLIENT_CLASS kwarg 已废弃)
# 这里直接使用 Django 自带的 django.core.cache.backends.redis.RedisCache
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
try:
    # 探测 Redis 是否可用
    import socket
    from urllib.parse import urlparse
    parsed = urlparse(REDIS_URL)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    _redis_reachable = sock.connect_ex((parsed.hostname or 'localhost', parsed.port or 6379)) == 0
    sock.close()
except Exception:
    _redis_reachable = False

if _redis_reachable:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': 'ats',
            'TIMEOUT': 300,
        }
    }
else:
    # Redis 不可用 - 使用本地内存缓存（仅开发/测试用）
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'ats-locmem',
            'TIMEOUT': 300,
        }
    }

# === Celery ===
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    'check-stage-time-limit': {
        'task': 'apps.time_limit.tasks.check_stage_time_limit',
        'schedule': 30 * 60,  # 30 分钟
    },
    'auto-advance-scheduler': {
        'task': 'apps.automation.tasks.run_scheduled_rules',
        'schedule': 15 * 60,  # 15 分钟
    },
    'talent-pool-recommendation': {
        'task': 'apps.talent_pool.tasks.recommend_candidates',
        'schedule': 60 * 60,  # 1 小时
    },
    'cleanup-expired-invitations': {
        'task': 'apps.invitation.tasks.cleanup_expired',
        'schedule': 60 * 60,  # 1 小时
    },
    'gdpr-retention-cleanup': {
        'task': 'apps.gdpr.tasks.run_retention_cleanup',
        'schedule': 24 * 60 * 60,  # 24 小时
    },
}

# === Channels ===
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL')],
        },
    },
}

# === 限流 ===
RATELIMIT_ENABLE = env.bool('RATELIMIT_ENABLE', default=True)

# === 邮件 ===
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@example.com')

# === 企微/短信/外部集成 ===
WECOM_CORPID = env('WECOM_CORPID', default='')
WECOM_CORPSECRET = env('WECOM_CORPSECRET', default='')
WECOM_AGENTID = env('WECOM_AGENTID', default='')
SMS_PROVIDER = env('SMS_PROVIDER', default='mock')
SMS_API_KEY = env('SMS_API_KEY', default='')
MOKA_API_URL = env('MOKA_API_URL', default='')
MOKA_API_KEY = env('MOKA_API_KEY', default='')

# === 监控 ===
SENTRY_DSN = env('SENTRY_DSN', default='')
PROMETHEUS_ENABLED = env.bool('PROMETHEUS_ENABLED', default=False)

# === 日志 ===
LOG_LEVEL = env('LOG_LEVEL', default='INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter' if _HAS_JSON_LOGGER else 'logging.Formatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
        'verbose': {
            'format': '{asctime} [{levelname}] {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'ats.log',
            'maxBytes': 1024 * 1024 * 50,  # 50MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}

# === 自定义 ATS 配置 ===
ATS_BASE = {
    'GRAB_THRESHOLD_DEFAULT': 30,
    'TIME_LIMIT_DEFAULT_DAYS': 30,
    'AUTOMATION_DELAY_HOURS_OPTIONS': [0, 1, 2, 4, 8, 24],
    'AUTO_ADVANCE_P95_TARGET_MS': 200,
    'BATCH_SCAN_1000_TARGET_SECONDS': 30,
    'CHANNEL_FALLBACK_GRACE_HOURS': 4,
    'OFFER_DEFAULT_EXPIRE_DAYS': 7,
    'GDPR_RETENTION_DAYS': 365 * 5,  # 5 年
    'AUDIT_LOG_RETENTION_DAYS': 365 * 3,  # 3 年
    'TALENT_POOL_RETENTION_DAYS': 365 * 2,  # 2 年
}
