"""GDPR URL Routes - /api/v1/gdpr/..."""
from rest_framework.routers import DefaultRouter

from .views import GDPRRequestViewSet

router = DefaultRouter()
router.register(r'requests', GDPRRequestViewSet, basename='gdpr-request')

urlpatterns = router.urls
