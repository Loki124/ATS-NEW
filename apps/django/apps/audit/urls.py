"""Audit URL Routes - /api/v1/audit-logs/..."""
from rest_framework.routers import DefaultRouter

from .views import AuditLogViewSet

router = DefaultRouter()
router.register(r'', AuditLogViewSet, basename='audit-log')

urlpatterns = router.urls
