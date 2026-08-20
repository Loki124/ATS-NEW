"""校招管控路由（v2：适用范围 + 维度/指标/规则/人数目标）。"""
from rest_framework.routers import DefaultRouter

from .views import (
    ControlScopeViewSet, ControlDimensionViewSet, ControlIndicatorViewSet,
    ControlRuleViewSet, ControlHeadcountViewSet, PersonViewSet,
)

router = DefaultRouter()
router.register(r'scopes', ControlScopeViewSet, basename='campus-scope')
router.register(r'dimensions', ControlDimensionViewSet, basename='campus-dimension')
router.register(r'indicators', ControlIndicatorViewSet, basename='campus-indicator')
router.register(r'rules', ControlRuleViewSet, basename='campus-rule')
router.register(r'headcounts', ControlHeadcountViewSet, basename='campus-headcount')
router.register(r'persons', PersonViewSet, basename='campus-person')

urlpatterns = router.urls
