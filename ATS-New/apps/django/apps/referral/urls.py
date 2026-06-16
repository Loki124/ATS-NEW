"""Referral URL Routes - /api/v1/referrals/..."""
from rest_framework.routers import DefaultRouter

from .views import ReferralViewSet

router = DefaultRouter()
router.register(r'', ReferralViewSet, basename='referral')

urlpatterns = router.urls
