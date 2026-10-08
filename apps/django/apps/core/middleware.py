"""Core 中间件"""
import logging
import uuid

from django.middleware.csrf import CsrfViewMiddleware

logger = logging.getLogger(__name__)

# 招聘类型合法值 (与 reason_library.RecruitType 对齐); 惰性加载避免 app 加载期循环导入.
_VALID_RECRUIT_TYPES = None


def _valid_recruit_types():
    global _VALID_RECRUIT_TYPES
    if _VALID_RECRUIT_TYPES is None:
        from apps.reason_library.models import RecruitType
        _VALID_RECRUIT_TYPES = frozenset({RecruitType.SOCIAL.value, RecruitType.CAMPUS.value})
    return _VALID_RECRUIT_TYPES


class RequestIdMiddleware:
    """为每个请求注入 request_id"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get('X-Request-Id') or uuid.uuid4().hex[:16]
        request.request_id = request_id
        response = self.get_response(request)
        response['X-Request-Id'] = request_id
        return response


class ConditionalCsrfMiddleware(CsrfViewMiddleware):
    """
    对 /api/ 路径禁用 CSRF 检查。

    背景：本项目后端是 DRF JWT API（不是 Django 传统 session-cookie 模板渲染）。
    前端是 Vue SPA，登录走 /api/v1/auth/login/，认证用 Authorization: Bearer <jwt>。
    但是浏览器通过 vite proxy (localhost:5212 → localhost:8000) 访问后端时，
    因为是同源代理，会自动带上 5212 域的 csrftoken + sessionid cookie，
    触发 Django CsrfViewMiddleware 拦截，导致所有 POST /api/v1/* 返回 403。

    修复：
    1. 本中间件对 /api/ 路径直接跳过 CSRF（return None 跳过 process_view）。
    2. 同时配套设置 REST_FRAMEWORK 移除 SessionAuthentication
       （让 DRF 只走 JWT，不走 session/CSRF）。
    3. /admin/ 等非 API 路径仍保留 CSRF 校验（管理员后台需要 session+CSRF）。

    注意：API 路径豁免 CSRF 是安全的，因为 JWT 认证不需要 CSRF 保护；
    CSRF 攻击只能针对 session-based 认证，而本项目 API 不接受 session。
    """

    # 不需要 CSRF 的路径前缀
    CSRF_EXEMPT_PREFIXES = ('/api/',)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        # API 路径直接跳过 CSRF
        for prefix in self.CSRF_EXEMPT_PREFIXES:
            if request.path.startswith(prefix):
                return None
        # 其他路径（admin 等）走 Django 标准 CSRF
        return super().process_view(request, callback, callback_args, callback_kwargs)


class RecruitTypeMiddleware:
    """解析 X-Recruit-Type 请求头, 将当前招聘系统上下文注入 request.recruit_type.

    社会招聘 / 校园招聘 是同一后端的两条硬数据分区, 所有业务查询与写入
    都须按 request.recruit_type 隔离 (含超管, 不受行级 scope 豁免影响).

    - 缺省 / 非法值 -> 回落 'social' 并 log warning (防伪造请求头绕过分区)
    - 合法值: 'social' | 'campus' (与 reason_library.RecruitType 对齐)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw = (request.headers.get('X-Recruit-Type') or '').strip()
        if raw in _valid_recruit_types():
            request.recruit_type = raw
        else:
            if raw:
                logger.warning(
                    '[RecruitTypeMiddleware] 非法 X-Recruit-Type=%r, 回落 social', raw
                )
            request.recruit_type = 'social'
        return self.get_response(request)
