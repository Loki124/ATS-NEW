"""Position URL Routes - /api/v1/positions/..."""
from rest_framework.routers import DefaultRouter

from .views import PositionViewSet

router = DefaultRouter()
router.register(r'', PositionViewSet, basename='position')

urlpatterns = router.urls
