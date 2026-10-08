"""Time Limit URL"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TimeLimitRuleViewSet

router = DefaultRouter()
router.register(r'', TimeLimitRuleViewSet, basename='time-limit-rule')

urlpatterns = [
    path('', include(router.urls)),
]
