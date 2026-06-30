"""Integration URL Routes - /api/v1/integrations/..."""
from rest_framework.routers import DefaultRouter

from .views import IntegrationConfigViewSet, IntegrationSyncLogViewSet

router = DefaultRouter()
router.register(r'', IntegrationConfigViewSet, basename='integration-config')
router.register(r'', IntegrationSyncLogViewSet, basename='integration-sync-log')

urlpatterns = router.urls
