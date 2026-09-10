"""
Django settings for ATS Recruitment Management System.

生产环境请使用 config.settings.prod
开发环境使用 config.settings.dev
测试环境使用 config.settings.test
"""

from pathlib import Path
from datetime import timedelta
import os

# P1-4: Celery beat crontab 表达式支持
from celery.schedules import crontab  # noqa: E402

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
# 2026-06-29 拍平后: base.py 在 apps/django/config/settings/base.py
#   parent x3 = /opt/ats/ATS-New/apps/django  (Django 项目目录)
# 保持原结构 — 所有路径 (.env, staticfiles, logs, manage.py) 仍在 apps/django/
# STATICFILES_DIRS 是唯一例外 — 前端 dist 在 BASE_DIR.parent/web/app/dist
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # noqa

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

# 2026-07-02: HTTPS / cookie 安全 (生产环境由 prod.py 强制开启)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# session/cookie 安全 - dev/staging 默认 False (HTTP 本地), prod.py 覆盖
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True  # JS 不需读 csrftoken
CSRF_COOKIE_SAMESITE = 'Lax'

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
    # 2026-06-17: G30 RPA 简历抓取 — 新 app
    # 2026-06-17: G41 数据字典 — 枚举值 single source of truth
    'apps.dictionary',
    'apps.notification',
    'apps.gdpr',
    'apps.integration',
    'apps.common',
    # 流程域
    'apps.process',
    'apps.entry_condition',
    'apps.time_limit',
    'apps.automation',
    'apps.rule_engine',     # 2026-08-31: Phase 0 统一规则引擎核心脚手架（仅新增，不动现有调用方）
    # 业务域
    'apps.candidate',
    'apps.add_candidate',  # 2026-06-22: 新版创建候选人流程
    'apps.application',
    'apps.demand',
    'apps.position',
    'apps.offer',
    'apps.onboarding',
    'apps.invitation',
    'apps.interview',
    'apps.referral',
    'apps.search',         # 全局统一搜索端点 (Plan P), 无 model, 仅 APIView
    'apps.resume_flow',    # Phase 2 T06: 审批流独立 app
    'apps.talent_pool',
    'apps.channel',
    'apps.analytics',

    'apps.mou',             # 2026-07-01 花无缺: MOU 业务 (大客户协议), 暂未挂 config/urls (stub 在 referral/urls_stubs)
    'apps.library',         # G41 院校/公司信息库
    # Phase 2 T02 (寇豆码): scraped_resume 已补 model 保留; duplicate_check 已于 2026-09-05 删除
    #   - scraped_resume  已补 ScrapedResume 最小 model (G30 完整功能由 T06 落地)
    #   - duplicate_check  原 7 处前端调用已萎缩为 1 处死文件引用 (AddCandidateModal.legacy.vue 的
    #     import type), G45 查重真实现已迁 apps.add_candidate/services/duplicate_check.py,
    #     stub 返空假数据属假绿, 删除 (决策依据: docs/PHASE2_DESIGN_2026-08-03.md §T02)
    'apps.scraped_resume',
    'apps.dynamic_field',   # G42 动态字段定义 — admin 自定义 Candidate/Position 等资源字段
    'apps.brand',           # G43 品牌信息管理 — 雇主品牌文案 / Logo / 招聘门户展示信息（单例配置）
    'apps.standard_resume',  # 标准简历配置（候选人标准简历字段与必填规则）落库
    'apps.announcement',
    'apps.campus_control',  # 校招管控（人员比例管控系统）    # 制度公告 — 招聘专家查看 / HR 及以上维护
    'apps.external_sync',  # G40 Mock 占位端点 (无 model, 仅 APIView). 还原 T02 删除: 前端 CompanySettings 显式 Mock 页仍真实调用, 不能 404
]  # Phase 2 T02 (寇豆码): 原删 'apps.data' / 'apps.external_sync' 两个 0-model 空壳 app; data 已重建为 analytics(/data/), external_sync 重建为 mock 端点(/external-sync/)
                          #   上游 grep 0 调用方, 无 model 无迁移. 详见 §T02.

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# === 中间件 ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 2026-06-16: 替换 Django 原生 CsrfViewMiddleware 为 ConditionalCsrfMiddleware
    # 原因：API 走 JWT 不需要 CSRF，但浏览器 vite proxy 同源会带 csrftoken cookie 触发 403
    # /admin/ 等非 API 路径仍走 Django 标准 CSRF
    'apps.core.middleware.ConditionalCsrfMiddleware',
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
    # 优先用独立环境变量拼装, 避免密码含 / 等字符导致 DATABASE_URL 解析失败
    # (docker compose 会原样注入这些变量, 无需 URL encode)
    mysql_host = env('MYSQL_HOST', default=None)
    mysql_user = env('MYSQL_USER', default=None)
    mysql_password = env('MYSQL_PASSWORD', default=None)
    mysql_database = env('MYSQL_DATABASE', default=None)
    if all([mysql_host, mysql_user, mysql_password is not None, mysql_database]):
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': mysql_database,
                'USER': mysql_user,
                'PASSWORD': mysql_password,
                'HOST': mysql_host,
                'PORT': env('MYSQL_PORT', default='3306'),
                'OPTIONS': {
                    'charset': 'utf8mb4',
                    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                },
            }
        }
    else:
        # 兼容本地/测试等直接使用 DATABASE_URL 的环境
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
# Static files (admin/rest_framework served by whitenoise from STATIC_ROOT)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# 2026-06-29 拍平: 前端 dist 在项目根下 web/app/dist, 不是 apps/django/web/app/dist.
# collectstatic 会把 src 1 (admin) + src 2 (前端 dist) 都拷到 STATIC_ROOT,
# 然后 whitenoise /static/* 一起 serve.
STATICFILES_DIRS = [
    BASE_DIR.parent.parent / 'web' / 'app' / 'dist',
]  # 2026-06-29 拍平: 前端 dist 在项目根下 web/app/dist, 不是 apps/django/web/app/dist
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

# Default deny-by-default shadow toggle. Keep False in production.
ATSSEC_DRY_RUN = False

# === 统一规则引擎 双写 / 委托开关（Phase 2，2026-08-31，设计文档 §3.2 / §6 Phase 2）===
# 双写（默认开）：automation 记录保存/软删时，best-effort 镜像到 rule_engine 统一表。
#   仅新增镜像、不改现网行为；异常仅记日志。灰度期保持开启以积累镜像数据。
RULE_ENGINE_DOUBLE_WRITE = env.bool('RULE_ENGINE_DOUBLE_WRITE', default=True)
# 委托（默认关）：automation 执行改走统一引擎 RuleEngine。开启前现网行为不变；
#   仅在双写稳定、executor 经测试验证后，按流程逐个 trigger 打开。
RULE_ENGINE_DISPATCH = env.bool('RULE_ENGINE_DISPATCH', default=False)

# === DRF 配置 ===
REST_FRAMEWORK = {
    # 2026-06-16: 移除 SessionAuthentication，只保留 JWT
    # 原因：API 是无状态的，前端用 Authorization: Bearer <jwt> 认证
    # SessionAuthentication 会强制 CSRF 校验，浏览器 vite proxy 同源会带 csrftoken cookie 触发 403
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'apps.core.permissions.IsAuthenticatedDenyByDefault',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        # 2026-06-17: API 边界 snake_case ↔ camelCase 自动转换 (djangorestframework-camel-case)
        # 出: Python snake_case → JSON camelCase (FE 直接消费, 无需手桥)
        # 入: 见 DEFAULT_PARSER_CLASSES
        # 不变: 单词字段 (id, username, roles, permissions, access, refresh) + 字典 key (例如自由文本 dict)
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        # 入: FE 发 camelCase → DRF serializer 看到 snake_case
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
    # 2026-09-03: 关掉 DRF 默认 URL format 协商拦截 (默认 'format' query param)
    # 原因: G35 数据导出 /api/v1/data/export/<resource>/?format=csv 走 csv 流式 (text/csv)
    #   DRF default renderers 只有 JSONRenderer, 收到 ?format=csv 直接 404 "未找到"
    #   关掉后 view 自己读 query_params.get('format') 走流式响应.
    'URL_FORMAT_OVERRIDE': None,
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '1000/minute',
        # Fix 6: 登录端点限速 5/min/IP, 防密码爆破
        'login': '5/minute',
        # 2026-07-02: 注册 + 改密限速, 防撞库和 spam account
        'register': '3/hour',
        'change_password': '5/minute',
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

# 2026-06-16: CSRF_TRUSTED_ORIGINS - 允许浏览器同源 vite proxy 跨域 POST
# (虽然 ConditionalCsrfMiddleware 已经对 /api/ 豁免 CSRF，但保留这个以防 Django
# 其他中间件做 Origin 检查)
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5212',
    'http://127.0.0.1:5212',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

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
    # P1-4: audit log 清理任务
    'audit-log-cleanup': {
        'task': 'apps.audit.tasks.cleanup_old_audit_logs',
        # 每日凌晨 3:00 执行 (crontab: 0 3 * * *)
        'schedule': crontab(hour=3, minute=0),
    },
    'audit-cleanup-healthcheck': {
        'task': 'apps.audit.tasks.audit_cleanup_healthcheck',
        'schedule': 60 * 60,  # 1 小时
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

# ===== Add Candidate V2 - 第三方 API 配置 =====
# 2026-06-22: 商业简历解析服务 (Affinda)
# 生产环境通过环境变量注入，本地开发用 .env
AFFINDA_API_KEY = env('AFFINDA_API_KEY', default='test_affinda_key_dev')

# Fix 6: 集成凭据 Fernet 加密密钥 (32-byte base64, 用 `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 生成).
# 必须在 .env / 生产环境注入; 未配置时 IntegrationConfig 加密迁移会跳过但运行期 _get_decrypted_config 会 RuntimeError.
INTEGRATION_FERNET_KEY = env('INTEGRATION_FERNET_KEY', default='')

# 2026-08-03 S3: PII 字段加密 (Candidate.id_card_no 等) 复用同一 Fernet key.
#   推荐单独设 ENCRYPTION_KEY, 但 fallback 到 INTEGRATION_FERNET_KEY (同算法可复用)
ENCRYPTION_KEY = env('ENCRYPTION_KEY', default=INTEGRATION_FERNET_KEY)
AFFINDA_BASE_URL = env('AFFINDA_BASE_URL', default='https://api.affinda.com/v3')
AFFINDA_WORKSPACE = env('AFFINDA_WORKSPACE', default='ats-default')
AFFINDA_DOCUMENT_TYPE = env('AFFINDA_DOCUMENT_TYPE', default='resume')

# 解析超时（秒）
AFFINDA_TIMEOUT_SECONDS = int(env('AFFINDA_TIMEOUT_SECONDS', default=30))

# 评分及格线
SCORING_PASS_THRESHOLD = int(env('SCORING_PASS_THRESHOLD', default=60))
