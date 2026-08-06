"""Application URL Routing - /api/v1/applications/...

路由布局：
- /api/v1/applications/            ApplicationViewSet (申请, 含 14 个 @action)
- /api/v1/applications/<id>/       ApplicationViewSet

⚠️ 修复记录 (2026-08-06 寇豆码): 原实现 ApplicationViewSet / GrabPoolViewSet /
InvitationViewSet 三个 ViewSet 共用同一个 DefaultRouter 且都 register(r'')：
1. GrabPoolViewSet 全部路由被 ApplicationViewSet 吃掉 → 已拆到
   apps/application/urls_grab_pool.py，挂载在 /api/v1/grab-pool/。
2. apps/application/views.InvitationViewSet 与 apps/invitation/views.InvitationViewSet
   同名同 basename='invitation'，两处注册导致 URL name 冲突（reverse 结果不确定），
   且其 list/create/respond/send 路由本就被 ApplicationViewSet 吃掉。
   统一由 apps/invitation/urls.py 挂载 /api/v1/invitations/，此处不再注册。
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ApplicationViewSet

router = DefaultRouter()
router.register(r'', ApplicationViewSet, basename='application')

urlpatterns = [
    path('', include(router.urls)),
]
