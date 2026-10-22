"""开发环境配置

DATABASES 不再覆盖 base.py 的配置 - 由 DATABASE_URL 决定（统一 MySQL）
开发/测试环境统一使用 MySQL, 不再使用 SQLite；.env 中 DATABASE_URL 指向本地 MySQL (ats_dev)。
"""
from .base import *  # noqa
from .base import INSTALLED_APPS, MIDDLEWARE

# 本项目管理使用 MySQL，但不依赖 Postgres：移除 django.contrib.postgres 以避免引入 psycopg2 依赖
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django.contrib.postgres']

DEBUG = True
INTERNAL_IPS = ['127.0.0.1']

# 关闭限流
RATELIMIT_ENABLE = False

# 开发环境放宽 DRF 注册限速，避免测试时 3 次/小时被卡死
REST_FRAMEWORK = REST_FRAMEWORK.copy()
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    **REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}),
    'register': '30/minute',
}

# CORS 允许所有（仅开发）
CORS_ALLOW_ALL_ORIGINS = True

# 关闭 CSRF（仅开发，配合 DRF Token 认证）
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# 邮件
# 2026-10-18: 改为 env 驱动 (默认仍 console) — .env 配好阿里云 DirectMail SMTP 后,
# 本地 dev 即可真实发信 (注册验证码流程真机联调); 不设 EMAIL_BACKEND 时行为不变。
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

# V2 启动校验: dev 默认禁用, 配合 `python manage.py migrate` / `seed_v2_init` 等初始化阶段使用
# 设 PERMISSION_V2_BOOTSTRAP_DISABLED=1 (在 .env 或 shell) 暂时跳过启动校验
PERMISSION_V2_BOOTSTRAP_DISABLED = env.bool('PERMISSION_V2_BOOTSTRAP_DISABLED', default=False)

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

# 2026-10-21 卡 C4: 开发环境显式注入**非公开**的 PII hash salt。
#   此前 base.py 的默认值是空串 → 意为「沿用源码内置的历史 salt 'ats-pii'」，
#   而本仓库公开 → 该 salt 已知 → 手机号空间仅 ~10^10，可被离线预计算反查。
#   这里给开发环境一个显式默认值（.env 里有真 salt 时仍以 .env 为准），
#   保证 dev 不会静默用着公开的 legacy salt。
#   ⚠️ 该值仅供本地**假数据**使用，生产必须由部署环境注入随机 salt
#      （config/settings/prod.py 对空值会直接拒绝启动）。
PII_HASH_SALT = env('PII_HASH_SALT', default='ats-dev-only-salt-2026-not-for-prod')
