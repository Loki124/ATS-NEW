"""测试环境配置"""
from urllib.parse import unquote, urlsplit

from .base import *  # noqa


def _resolve_db_password() -> str:
    """解析测试库口令 —— **源码内不保留任何真实凭据**。

    2026-10-21 卡 A7：此前此处硬编码了本地 MySQL 明文口令（已随仓库分发），
    改为按优先级从环境取：
      ① DB_PASSWORD 环境变量（CI 与容器部署用）
      ② MYSQL_PASSWORD 环境变量
      ③ .env 的 DATABASE_URL 解析（base.py:48-51 已把 .env 读进 os.environ，
         而 .env 本身被 .gitignore 覆盖，属本地未跟踪文件）

    取不到时返回空串并由 MySQL 驱动报「Access denied」—— 报错信息可读，
    好过在源码里留一个能被人直接拿去用的口令。
    """
    for key in ('DB_PASSWORD', 'MYSQL_PASSWORD'):
        val = os.environ.get(key)
        if val:
            return val
    url = os.environ.get('DATABASE_URL', '')
    if url:
        try:
            parts = urlsplit(url)
        except ValueError:
            return ''
        if parts.password:
            return unquote(parts.password)
    return ''


DEBUG = True

# 测试环境允许所有 host
ALLOWED_HOSTS = ['*']

# 2026-10-15: 全仓约定 —— 开发/测试统一用 MySQL, SQLite 已完全移除。
#   根因教训: 此前本地/单测默认 SQLite, 掩盖了 0024 "RemoveField+AddField 同名列在 MySQL 上
#   DROP 整列丢数据" 的差异 (SQLite 整表重建会拷贝数据), 导致 "本地/CI 全绿、生产 1452"。
#   此后测试默认走 MySQL (本地 ats_test / CI mysql:8.0), 让 MySQL 特有行为差异在开发期就暴露。
#   项目已禁用 SQLite, 此处不再保留任何 SQLite / DB_ENGINE 分支。
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'ats_test'),
        # 本地默认复用 dev 库同款账号 (apps/django/.env), pytest 开箱即用;
        # CI 用 mysql:8.0 service 的 root + 密钥覆盖。
        'USER': os.environ.get('DB_USER', 'ats_dev'),
        'PASSWORD': _resolve_db_password(),
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

# 2026-10-13 (权限 v2): 同理关闭动作字典缓存。test_write_actions 里会停用动作
#   （delete/merge），TTL 缓存会让后续用例读到"已停用"的脏状态产生顺序依赖。
DP_ACTION_DICT_CACHE_TTL = 0

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

# 2026-10-21 卡 C4: 测试环境显式注入**测试专用** PII hash salt。
#   此前 base.py 默认空串 → 回落到源码内置的历史 salt 'ats-pii'（公开 → 手机号可离线反查）。
#   CI 的 .env 模板里该项留空 → 之前 CI 一直在用公开 salt。
#   这里给测试专用默认值（.env / 环境变量有值时仍以其为准），
#   让 CI 也走 v2 哈希路径（与生产同构），而不是悄悄用公开 salt。
#   ⚠️ 仅供测试的**假数据**使用；生产必须由部署环境注入随机 salt
#      （config/settings/prod.py 对空值会直接拒绝启动）。
PII_HASH_SALT = env('PII_HASH_SALT', default='ats-test-only-salt-2026-not-for-prod')
