"""校招管控路由（v2.4：维度/指标/规则[含人数目标]/人员，规则自带适用范围）。"""
from rest_framework.routers import DefaultRouter

from .views import (
    ControlDimensionViewSet,
    ControlIndicatorViewSet,
    ControlRuleViewSet,
    PersonViewSet,
)

router = DefaultRouter()
router.register(r'dimensions', ControlDimensionViewSet, basename='campus-dimension')
router.register(r'indicators', ControlIndicatorViewSet, basename='campus-indicator')
router.register(r'rules', ControlRuleViewSet, basename='campus-rule')
router.register(r'persons', PersonViewSet, basename='campus-person')

urlpatterns = router.urls
