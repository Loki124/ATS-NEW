"""Talent Pool URL Routes - /api/v1/talent-pool/..."""
from rest_framework.routers import DefaultRouter

from .views import TalentPoolEntryViewSet, TalentPoolTagViewSet

router = DefaultRouter()
router.register(r'', TalentPoolEntryViewSet, basename='talent-pool-entry')
router.register(r'', TalentPoolTagViewSet, basename='talent-pool-tag')

urlpatterns = router.urls
