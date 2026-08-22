"""Auth URL 路由"""
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views_auth import login_view, logout_view, me_view, change_password_view

# T01.2 (2026-08-04 寇豆码): 显式声明 AllowAny, 覆盖全局 deny-by-default.
#   TokenRefresh/TokenVerify 本身就是公开端点 (拿 refresh token 换新 access), 不应被
#   IsAuthenticatedDenyByDefault 拦截.
TokenRefreshView.permission_classes = [AllowAny]
TokenVerifyView.permission_classes = [AllowAny]

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('me/', me_view, name='me'),
    path('change-password/', change_password_view, name='change-password'),
]
