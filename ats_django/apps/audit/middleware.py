"""Audit Middleware (PRD v4 §13, §4.4)

记录所有非 GET 请求的写操作 + 敏感字段访问。
注意：仅做最轻量的记录（不阻断请求），详细审计由各模块的 signals/service 完成。
"""
import json
import logging
import time

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


class AuditMiddleware:
    """审计中间件 - 轻量记录写操作

    完整审计字段（user/old_value/new_value 等）由 AuditLog model + 各 app 的 signals
    维护；本中间件仅记录请求基本信息（IP/UA/RequestId/method/path/duration）。
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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
                # 审计失败不能影响业务
                logger.warning('AuditMiddleware record failed: %s', e)

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
