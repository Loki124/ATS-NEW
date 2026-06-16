"""Automation URL Config"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AutomationLogViewSet, AutomationRuleViewSet, AutomationTriggerView

router = DefaultRouter()
router.register(r'', AutomationRuleViewSet, basename='automation-rule')
router.register(r'logs', AutomationLogViewSet, basename='automation-log')

trigger_view = AutomationTriggerView.as_view({'post': 'create'})

urlpatterns = [
    path('trigger', trigger_view, name='automation-trigger'),
    path('', include(router.urls)),
]
