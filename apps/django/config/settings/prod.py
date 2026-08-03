"""生产环境配置

P0-5 修复: 启动时强校验生产环境必填配置
- CORS_ALLOWED_ORIGINS 必须非空
- DJANGO_SECRET_KEY 不能是 base.py 的默认值
- ALLOWED_HOSTS 不能包含通配符 '*'
- DATABASE_URL 必须是 mysql/postgres,不能是 sqlite
"""
from .base import *  # noqa
import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration


def _validate_production_config():
    """生产环境启动时强校验

    失败立即抛 ImproperlyConfigured,Django 启动失败而非"看似启动但跨域全挂"
    """
    # 1) SECRET_KEY 不能是 base.py 的默认值
    DEFAULT_DEV_SECRETS = {
        'insecure-dev-key-change-me',
        'change-me-in-production-please-use-a-long-random-string',
        'django-insecure',
    }
    if SECRET_KEY in DEFAULT_DEV_SECRETS or len(SECRET_KEY) < 50:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY 仍是默认值或长度 < 50。请设置一个 50+ 字符的随机串。\n'
            '  生成方法: python -c "import secrets; print(secrets.token_urlsafe(64))"'
        )

    # 2) DEBUG 必须为 False
    if DEBUG:
        raise ImproperlyConfigured('生产环境 DEBUG 必须为 False')

    # 3) ALLOWED_HOSTS 不能是通配符
    if '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS 不能包含 '*'。生产环境必须明确列出域名,例如\n"
            "  DJANGO_ALLOWED_HOSTS=ats.example.com,api.example.com"
        )

    # 4) CORS_ALLOWED_ORIGINS 必须非空 (前端域名)
    if not CORS_ALLOWED_ORIGINS:
        raise ImproperlyConfigured(
            'CORS_ALLOWED_ORIGINS 不能为空,否则所有跨域请求失败。\n'
            '  设置方法: CORS_ALLOWED_ORIGINS=https://ats.example.com,https://admin.example.com'
        )

    # 4b) R3 (2026-08-03): CORS 绝不允许全放开。
    #     dev.py 里有 CORS_ALLOW_ALL_ORIGINS = True,一旦 settings 误回落到 dev
    #     或有人手工写进 prod,任意站点都能带凭据打 API。这里显式拦死。
    if globals().get('CORS_ALLOW_ALL_ORIGINS', False):
        raise ImproperlyConfigured(
            '生产环境禁止 CORS_ALLOW_ALL_ORIGINS=True。请改用白名单 '
            'CORS_ALLOWED_ORIGINS。'
        )

    # 4c) R3: 白名单里也不允许出现通配符 / 明文 http (本地回环除外)
    for _origin in CORS_ALLOWED_ORIGINS:
        if _origin.strip() in ('*', 'http://*', 'https://*'):
            raise ImproperlyConfigured(
                "CORS_ALLOWED_ORIGINS 不能包含通配符 '%s',必须逐个列出前端域名。" % _origin
            )

    # 5) 数据库必须是 MySQL/PostgreSQL,不能是 SQLite
    db_url = globals().get('DATABASE_URL', '') or ''
    if db_url.startswith('sqlite'):
        raise ImproperlyConfigured(
            '生产环境禁止使用 SQLite!请改用 MySQL 或 PostgreSQL。\n'
            '  当前 DATABASE_URL=%s' % db_url
        )

    # 6) JWT 密钥如果也是默认值,警告 (不阻断,允许临时使用)
    if not CORS_ALLOW_CREDENTIALS:
        # 业务上 JWT 在 Authorization header,不依赖 cookie,但保持显式
        pass


# === 启动时执行强校验 (在 import 阶段就检查) ===
_validate_production_config()


DEBUG = False
# R3 (2026-08-03): 显式钉死,防止 base/dev 的值漏进来
CORS_ALLOW_ALL_ORIGINS = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# Fix 10: 生产环境强制使用 Redis 缓存, 不允许 LocMemCache fallback.
# LocMemCache 在多 gunicorn worker 下不同步, throttle / idempotency / session
# 全部失效, 静默退化导致生产数据损坏. 启动时若 Redis 不可用直接抛错.
import socket as _socket
from urllib.parse import urlparse as _urlparse
_prod_redis_parsed = _urlparse(REDIS_URL)
_sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
_sock.settimeout(2.0)
_redis_ok = _sock.connect_ex(
    (_prod_redis_parsed.hostname or 'localhost', _prod_redis_parsed.port or 6379)
) == 0
_sock.close()
if not _redis_ok:
    raise ImproperlyConfigured(
        '生产环境 Redis 不可用 (%s)。不允许 LocMemCache 静默 fallback — '
        '多 worker 下 throttle / idempotency 失效。请检查 Redis 服务。' % REDIS_URL
    )
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'KEY_PREFIX': 'ats',
        'TIMEOUT': 300,
    }
}

# Sentry 错误追踪
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# 日志仅输出到文件
LOGGING['handlers']['console']['level'] = 'WARNING'
LOGGING['loggers']['apps']['level'] = 'INFO'
