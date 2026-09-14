"""注册审核 URL 路由 (挂在 core.urls_auth 的 auth/ 之下)."""
from django.urls import path

from .views import (
    register_view,
    verify_register_code_view,
    resend_register_code_view,
    registration_list_view,
    registration_approve_view,
    registration_reject_view,
)

urlpatterns = [
    # 自助注册 (AllowAny)
    path('register', register_view, name='register'),
    path('register/', register_view),
    path('verify-register-code', verify_register_code_view, name='verify-register-code'),
    path('verify-register-code/', verify_register_code_view),
    path('resend-register-code', resend_register_code_view, name='resend-register-code'),
    path('resend-register-code/', resend_register_code_view),

    # 管理员审核 (IsAuthenticated + SUPER_ADMIN)
    path('registrations/', registration_list_view, name='registration-list'),
    path('registrations/<str:pk>/approve/', registration_approve_view, name='registration-approve'),
    path('registrations/<str:pk>/reject/', registration_reject_view, name='registration-reject'),
]
