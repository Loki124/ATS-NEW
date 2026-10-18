"""邮箱验证码登录 URL 路由 (挂在 core.urls_auth 的 auth/ 之下)."""
from django.urls import path

from .views import email_login_view, send_login_code_view

urlpatterns = [
    # 邮箱验证码免密登录 (AllowAny)
    path('email-login/send-code', send_login_code_view, name='email-login-send-code'),
    path('email-login/send-code/', send_login_code_view),
    path('email-login/verify', email_login_view, name='email-login-verify'),
    path('email-login/verify/', email_login_view),
]
