"""校招管控路由（v2.4：维度/指标/规则[含人数目标]/人员，规则自带适用范围）。

命名澄清：本 app（campus_control）与 `campus` app **仅名字相近、职责完全不同**，请勿合并——
- `campus_control`（本 app）：校招**人员比例管控**系统（ControlRule/Indicator/Dimension + rule_engine 适配器）；
- `campus`：校园大使 / 宣讲会 / 校招模块开关（业务功能）。
两者是相互独立的两个业务域（本 app 挂 /api/v1/campus/，campus 挂 /api/v1/campus-recruit/）。"""
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
