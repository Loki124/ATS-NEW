"""Onboarding URL Routes - /api/v1/onboardings/..."""
from rest_framework.routers import DefaultRouter

from .views import OnboardingViewSet

router = DefaultRouter()
router.register(r'', OnboardingViewSet, basename='onboarding')

urlpatterns = router.urls
