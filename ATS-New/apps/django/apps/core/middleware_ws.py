"""Channels WebSocket 中间件 - JWT 认证

P1-1 修复: Token 传输改用 Sec-WebSocket-Protocol 子协议，
避免 token 出现在 URL/access log/Referer/中间件日志。

传输协议（按优先级）:
1. Sec-WebSocket-Protocol 子协议（推荐）:
   - 客户端格式: new WebSocket(url, ['jwt.token.<JWT>'])
   - 浏览器不会把 Sec-WebSocket-Protocol 写入 access log / Referer
   - 协议握手必须由服务端从客户端提议中选定一个
2. query string `?token=...` (向后兼容,不推荐,会泄露)

设计要点:
- 子协议名固定以 'jwt.token.' 前缀开头
- 服务端从 scope['subprotocols'] 中识别该前缀并提取 JWT
- 响应时 selected_subprotocol 设为 'jwt.token'（去掉 token 部分，符合 RFC 6455）
- 若客户端未使用子协议,降级到 query string
"""
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()

# 子协议前缀（RFC 6455 要求 subprotocol token 由可见 ASCII 字符组成，
# 标准实现不接受空格、点以外的特殊字符;但 JWT 本身是 base64-urlsafe，
# 字符集是 [A-Za-z0-9_-]，浏览器通常会接受 '.' 作为子协议分隔符）。
# 注意:部分浏览器（如 Chrome）对包含 '.' 的子协议处理不一致，
# 所以采用更稳健的设计:客户端把整个子协议名设为 'jwt.token.<JWT>'，
# 服务端匹配前缀即可。
SUBPROTOCOL_PREFIX = 'jwt.token.'
SUBPROTOCOL_PUBLIC = 'jwt.token'  # 服务端回给客户端的 subprotocol（不含 token）


@database_sync_to_async
def get_user_from_token(token):
    try:
        validated_token = UntypedToken(token)
        user_id = validated_token.get('user_id')
        return User.objects.get(id=user_id, is_active=True, deleted_at__isnull=True)
    except (InvalidToken, TokenError, User.DoesNotExist):
        return AnonymousUser()


def _extract_token_from_subprotocols(subprotocols):
    """从客户端提议的 subprotocols 中提取 JWT

    客户端格式: ['jwt.token.<JWT>']
    找到以 'jwt.token.' 开头的项,返回其后的部分。
    """
    for proto in subprotocols:
        if isinstance(proto, str) and proto.startswith(SUBPROTOCOL_PREFIX):
            token = proto[len(SUBPROTOCOL_PREFIX):]
            if token:  # 防止空 token
                return token
    return None


class JWTAuthMiddleware(BaseMiddleware):
    """WebSocket JWT 认证中间件"""

    async def __call__(self, scope, receive, send):
        subprotocols = scope.get('subprotocols', []) or []
        token = _extract_token_from_subprotocols(subprotocols)

        # 回退:若客户端没有用 subprotocol,允许从 query string 读取(向后兼容)
        if not token:
            query_string = scope.get('query_string', b'').decode()
            query_params = parse_qs(query_string)
            token = query_params.get('token', [None])[0]

        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()

        # 告知 channels 接受哪个 subprotocol
        # 客户端: new WebSocket(url, ['jwt.token.<token>'])
        # 握手响应: Sec-WebSocket-Protocol: jwt.token
        used_subprotocol = bool(
            any(isinstance(p, str) and p.startswith(SUBPROTOCOL_PREFIX) for p in subprotocols)
        )
        scope['subprotocols'] = [SUBPROTOCOL_PUBLIC] if used_subprotocol else []

        return await super().__call__(scope, receive, send)
