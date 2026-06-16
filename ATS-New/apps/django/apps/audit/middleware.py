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

from django.core.cache import cache

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


def _is_killed() -> bool:
    """是否已被熔断（kill switch）"""
    try:
        return bool(cache.get(KILL_SWITCH_KEY))
    except Exception:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
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
        except Exception:  # noqa: BLE001
            pass


def reset_audit_kill_switch() -> bool:
    """运维工具: 手动清除熔断。

    用法: python manage.py shell -c "from apps.audit.middleware import reset_audit_kill_switch; reset_audit_kill_switch()"
    """
    try:
        cache.delete(KILL_SWITCH_KEY)
        cache.delete(AUDIT_FAIL_COUNT_KEY)
        logger.info('AuditMiddleware: 熔断已手动重置')
        return True
    except Exception as exc:  # noqa: BLE001
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
            except Exception as e:  # noqa: BLE001
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
        if logger.isEnabledFor(logging.DEBUG):
            body_summary = ''
            if request.method not in SKIP_METHODS and request.body:
                try:
                    raw = request.body[:512].decode('utf-8', errors='replace')
                    body_summary = raw
                except Exception:  # noqa: BLE001
                    body_summary = '<binary>'

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
