"""Notification URL Routes - /api/v1/notifications/..."""
from rest_framework.routers import DefaultRouter

from .views import NotificationLogViewSet, NotificationTemplateViewSet

router = DefaultRouter()
router.register(r'templates', NotificationTemplateViewSet, basename='notification-template')
router.register(r'', NotificationLogViewSet, basename='notification-log')

urlpatterns = router.urls
