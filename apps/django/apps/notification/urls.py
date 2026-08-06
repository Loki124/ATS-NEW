"""Notification URL Routes - /api/v1/notifications/...

路由布局：
- /api/v1/notifications/                  NotificationTemplateViewSet (通知模板)
- /api/v1/notifications/<pk>/             NotificationTemplateViewSet
- /api/v1/notifications/logs/             NotificationLogViewSet      (通知记录, 只读)
- /api/v1/notifications/logs/<pk>/        NotificationLogViewSet
- /api/v1/notifications/logs/unread/      NotificationLogViewSet.unread
- /api/v1/notifications/logs/unread-count/NotificationLogViewSet.unread_count
- /api/v1/notifications/logs/mark-read/   NotificationLogViewSet.mark_read

⚠️ 修复记录 (2026-08-06 寇豆码): 原实现两个 ViewSet 都 register(r'')，
NotificationLogViewSet 的 list/detail 路由被先注册的 Template 完全吃掉 → 不可达。
子资源前缀 `logs` 必须先于 r'' 注册。
"""
from rest_framework.routers import DefaultRouter

from .views import NotificationLogViewSet, NotificationTemplateViewSet

router = DefaultRouter()
# 子资源前缀必须先注册：否则被 r'' 的 `^(?P<pk>[^/.]+)/$` 当 pk='logs' 吃掉
router.register(r'logs', NotificationLogViewSet, basename='notification-log')
router.register(r'', NotificationTemplateViewSet, basename='notification-template')

urlpatterns = router.urls
