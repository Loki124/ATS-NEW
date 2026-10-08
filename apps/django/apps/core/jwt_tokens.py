"""2026-10-09 (#19): 在 simplejwt token 中嵌入 token_version claim。

simplejwt 默认不撤销已签发的 refresh token (无状态), 改密/禁用后旧 refresh 仍能换新
access。解决办法: 登录/刷新签发时把用户当前 ``token_version`` 写进 token; 刷新端点
(apps.core.views_auth.TokenRefreshViewWithVersion) 在换新前校验该 claim, 不一致即拒绝。
access 有效期本身已缩短 (SIMPLE_JWT.ACCESS_TOKEN_LIFETIME), 进一步压缩被盗用窗口。
"""
from rest_framework_simplejwt.tokens import RefreshToken


class MyRefreshToken(RefreshToken):
    """签发时把 ``user.token_version`` 写进 refresh payload (随之复制到 access)。"""

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token['token_version'] = getattr(user, 'token_version', 0)
        return token
