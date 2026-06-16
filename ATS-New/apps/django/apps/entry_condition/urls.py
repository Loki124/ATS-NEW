"""Entry Condition URL Config"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import EntryConditionRuleViewSet

router = DefaultRouter()
router.register(r'', EntryConditionRuleViewSet, basename='entry-condition-rule')

urlpatterns = [
    path('', include(router.urls)),
]
