"""Audit Middleware (PRD v4 §13, §4.4)

记录所有非 GET 请求的写操作 + 敏感字段访问。
注意：仅做最轻量的记录（不阻断请求），详细审计由各模块的 signals/service 完成。

P1-2 修复: 写库失败时降级 + 速率限制
- 失败时 cache.incr 累计失败次数
- 累计 > THROTTLE 阈值后改为 ERROR 级别,避免 log 爆炸
- 累计 > KILL_SWITCH 阈值后临时禁用中间件,直到运维确认恢复
"""
import json
import logging
import time

import redis
from django.core.cache import cache
from django.db import DatabaseError

logger = logging.getLogger(__name__)

# 不记录的路径（静态资源 + 健康检查 + 文档）
SKIP_PATH_PREFIXES = (
    '/static/',
    '/media/',
    '/health',
    '/api/schema',
    '/api/docs',
    '/api/redoc',
    '/admin/jsi18n',
    '/favicon.ico',
)

# 不记录的方法
SKIP_METHODS = ('GET', 'HEAD', 'OPTIONS')

# === P1-2 限速配置 ===
AUDIT_FAIL_COUNT_KEY = 'audit:fail_count'  # 当前进程/实例的累计失败次数
AUDIT_FAIL_COUNT_TTL = 300  # 5 分钟未失败则清零

# 阈值（按严重度升级）
THROTTLE_THRESHOLD = 50      # 累计 50 次失败 → 升级到 ERROR
KILL_SWITCH_THRESHOLD = 500  # 累计 500 次失败 → 临时禁用中间件
KILL_SWITCH_KEY = 'audit:disabled'
KILL_SWITCH_TTL = 600  # 禁用 10 分钟,运维可手动重置

# === 2026-10-08: 请求体脱敏 ===
# 原实现在 DEBUG 下直接 `request.body[:512]` 写日志 —— 登录密码、refresh token、
# 验证码、候选人手机号/邮箱/身份证会原样落进日志, 而 dev 配置的 apps logger 正是
# DEBUG (dev.py:39-43)。日志一旦被共享/备份/采集, 等于明文凭据泄露。
#
# 规则: 永不记录原始请求体。只保留"哪些字段被提交了"这一结构信息, 值一律脱敏。
import re as _re

_SENSITIVE_KEY_RE = _re.compile(
    r'password|passwd|token|refresh|secret|authorization|cookie'
    r'|otp|smscode|captcha|apikey|api_key'
    r'|phone|mobile|email|idcard|id_card|ssn|cvv|cvc|card|bank'
    r'|verification|code',
    _re.I,
)

# 这些路径的请求体整体不记录任何字段结构
_REDACT_WHOLE_BODY_PATHS = (
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/api/v1/auth/change-password',
    '/api/v1/auth/refresh',
    '/api/v1/gdpr',
    '/api/v1/accounts/register',
)

_REDACTED = '<redacted>'
_MAX_VALUE_LEN = 32


def _redact_value(value):
    """标量值脱敏: 只保留类型与长度, 不保留内容。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return '<bool>'
    if isinstance(value, (int, float)):
        return '<num>'
    if isinstance(value, str):
        return f'<str len={len(value)}>' if len(value) > _MAX_VALUE_LEN else _REDACTED
    return f'<{type(value).__name__}>'


def _redact_structure(obj, depth=0):
    """递归脱敏: 保留键名结构, 值一律替换为占位符; 敏感键名本身也打码。"""
    if depth > 3:
        return '<deep>'
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = str(k)
            if _SENSITIVE_KEY_RE.search(key):
                out[key] = _REDACTED
            elif isinstance(v, (dict, list)):
                out[key] = _redact_structure(v, depth + 1)
            else:
                out[key] = _redact_value(v)
        return out
    if isinstance(obj, list):
        return [_redact_structure(v, depth + 1) for v in obj[:10]]
    return _redact_value(obj)


def safe_body_summary(request):
    """生成可安全写入日志的请求体摘要 (永不包含原始值)。"""
    if request.method in SKIP_METHODS:
        return ''
    path = getattr(request, 'path', '') or ''
    if any(path.startswith(p) for p in _REDACT_WHOLE_BODY_PATHS):
        return '<omitted: sensitive endpoint>'
    try:
        raw = request.body
    except Exception:  # noqa: BLE001 — body 已被消费或不可读, 跳过即可
        return '<unreadable>'
    if not raw:
        return ''
    if len(raw) > 8192:
        return f'<omitted: body too large ({len(raw)} bytes)>'
    try:
        parsed = json.loads(raw.decode('utf-8', errors='replace'))
    except (ValueError, UnicodeDecodeError):
        # 非 JSON (form-data / multipart 上传) —— 结构不可控, 整体跳过
        return '<omitted: non-json body>'
    return json.dumps(_redact_structure(parsed), ensure_ascii=False)[:512]


def _is_killed() -> bool:
    """是否已被熔断（kill switch）"""
    try:
        return bool(cache.get(KILL_SWITCH_KEY))
    except (redis.exceptions.RedisError, OSError, ValueError):  # 读 kill_switch cache 失败返 False (容错: cache 不可用 = 不熔断)
        return False


def _record_failure() -> int:
    """记录一次失败,返回累计失败次数。失败时返回 -1。

    使用 Django cache API:
    - 生产 Redis: 真实原子
    - 开发 locmem: 进程内原子
    - 计数器带 TTL,故障恢复后自动重置
    """
    try:
        try:
            count = cache.incr(AUDIT_FAIL_COUNT_KEY)
        except ValueError:
            # key 不存在,初始化为 1
            cache.add(AUDIT_FAIL_COUNT_KEY, 1, timeout=AUDIT_FAIL_COUNT_TTL)
            count = 1
        return int(count)
    except (redis.exceptions.RedisError, OSError, ValueError) as exc:  # 失败计数 cache 失败返 -1 (不影响后续熔断逻辑, 仅日志)
        logger.warning('AuditMiddleware: 失败计数失败: %s', exc)
        return -1


def _maybe_enable_kill_switch(count: int) -> None:
    """达到熔断阈值时,临时禁用中间件"""
    if count >= KILL_SWITCH_THRESHOLD:
        try:
            cache.set(KILL_SWITCH_KEY, '1', timeout=KILL_SWITCH_TTL)
            logger.error(
                'AuditMiddleware: 累计失败 %d 次,已临时禁用 %d 秒（运维可手动删除 cache key 重置）',
                count, KILL_SWITCH_TTL,
            )
        except (redis.exceptions.RedisError, OSError, ValueError):  # 熔断 cache 写失败不应阻断下次请求的审计 (cache 是 best-effort)
            logger.exception('AuditMiddleware 熔断 cache 写入失败 count=%d ttl=%d', count, KILL_SWITCH_TTL)


def reset_audit_kill_switch() -> bool:
    """运维工具: 手动清除熔断。

    用法: python manage.py shell -c "from apps.audit.middleware import reset_audit_kill_switch; reset_audit_kill_switch()"
    """
    try:
        cache.delete(KILL_SWITCH_KEY)
        cache.delete(AUDIT_FAIL_COUNT_KEY)
        logger.info('AuditMiddleware: 熔断已手动重置')
        return True
    except (redis.exceptions.RedisError, OSError, ValueError) as exc:  # 重置熔断 cache 失败返 False, 不影响主流程 (cache 是 best-effort)
        logger.exception('AuditMiddleware: 重置熔断失败: %s', exc)
        return False


class AuditMiddleware:
    """审计中间件 - 轻量记录写操作

    完整审计字段（user/old_value/new_value 等）由 AuditLog model + 各 app 的 signals
    维护；本中间件仅记录请求基本信息（IP/UA/RequestId/method/path/duration）。

    P1-2 容错:
    - 写库/计算失败时不再无脑 logger.warning（会撑爆日志）
    - 失败计数到阈值时降级为 ERROR 级别
    - 极端情况下熔断,避免持续 IO 失败
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # P1-2: 已被熔断 → 直接放行,不记录、不计数
        if _is_killed():
            return self.get_response(request)

        # 跳过静态资源/文档/健康检查
        if any(request.path.startswith(p) for p in SKIP_PATH_PREFIXES):
            return self.get_response(request)

        start_time = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start_time) * 1000)

        # 仅记录写操作 & 错误响应
        if request.method not in SKIP_METHODS or response.status_code >= 400:
            try:
                self._record(request, response, duration_ms)
            except (redis.exceptions.RedisError, DatabaseError, ValueError, TypeError, AttributeError, OSError) as e:  # 审计写入失败不应阻断业务响应, 走失败计数 + 熔断路径
                # P1-2: 累计失败次数,按严重度升级日志级别,避免撑爆日志
                count = _record_failure()
                if count >= THROTTLE_THRESHOLD:
                    logger.error(
                        'AuditMiddleware record failed (累计 %d 次,已升级到 ERROR）: %s',
                        count, e,
                    )
                    _maybe_enable_kill_switch(count)
                else:
                    logger.warning(
                        'AuditMiddleware record failed (累计 %d 次）: %s',
                        count, e,
                    )

        return response

    def _record(self, request, response, duration_ms):
        user = getattr(request, 'user', None)
        user_id = getattr(user, 'id', None) if user and user.is_authenticated else None

        # 仅 DEBUG 级别记录详细信息，避免日志爆炸
        # 2026-10-08: body 一律走 safe_body_summary() 脱敏, 不再写原始请求体
        if logger.isEnabledFor(logging.DEBUG):
            body_summary = safe_body_summary(request)

            logger.debug(
                'audit method=%s path=%s status=%s user=%s duration=%dms body=%s',
                request.method,
                request.path,
                response.status_code,
                user_id,
                duration_ms,
                body_summary,
            )
        else:
            logger.info(
                'audit method=%s path=%s status=%s user=%s duration=%dms',
                request.method,
                request.path,
                response.status_code,
                user_id,
                duration_ms,
            )
