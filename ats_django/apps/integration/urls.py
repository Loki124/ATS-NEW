"""Integration URL Routes - /api/v1/integrations/..."""
from rest_framework.routers import DefaultRouter

from .views import IntegrationConfigViewSet, IntegrationSyncLogViewSet

router = DefaultRouter()
router.register(r'configs', IntegrationConfigViewSet, basename='integration-config')
router.register(r'sync-logs', IntegrationSyncLogViewSet, basename='integration-sync-log')

urlpatterns = router.urls
