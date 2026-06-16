"""Demand URL Routes - /api/v1/demands/..."""
from rest_framework.routers import DefaultRouter

from .views import DemandViewSet

router = DefaultRouter()
router.register(r'', DemandViewSet, basename='demand')

urlpatterns = router.urls
