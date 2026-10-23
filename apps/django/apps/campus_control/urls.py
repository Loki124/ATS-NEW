"""校招管控路由（v2.4：维度/指标/规则[含人数目标]/人员，规则自带适用范围）。

命名澄清：本 app（campus_control）与 `campus` app **仅名字相近、职责完全不同**，请勿合并——
- `campus_control`（本 app）：校招**人员比例管控**系统（ControlRule/Indicator/Dimension + rule_engine 适配器）；
- `campus`：校园大使 / 宣讲会 / 校招模块开关（业务功能）。
两者是相互独立的两个业务域（本 app 挂 /api/v1/campus/，campus 挂 /api/v1/campus-recruit/）。

批次规则引擎（契约 §4.2）也挂在本 app 下：
  GET/POST/…  /batch-rules/                批次规则 CRUD
  GET         /batch-rules/preview/        实时预览（样例 + 命中统计）
  POST        /batch-rules/apply/          按规则回写人员批次（只补空值）
  POST        /batch-rules/recalc/         重算批次号（先预览，apply=true 才落库）
  GET/PUT     /batch-naming/               命名配置（单例）
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BatchNamingViewSet,
    BatchRuleViewSet,
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
# 2026-10-23 校招生全生命周期移植 · 契约 §4.2：批次规则引擎
router.register(r'batch-rules', BatchRuleViewSet, basename='campus-batch-rule')
router.register(r'batch-naming', BatchNamingViewSet, basename='campus-batch-naming')

# ⚠️ 自定义路径必须排在 **router.urls 之前**（与 `campus_rotation/urls.py` 同款约定）：
#    DRF router 的详情路由 `^{prefix}/(?P<pk>[^/.]+)/` 会抢先匹配任意子路径名。
#
#    `batch-naming/` 是**单例**端点（契约 §4.2：GET/PUT 同一条路径），
#    而 router 的 list 路由只映射 GET/POST → PUT 必须显式挂 path()。
#    显式 path 放在 router.urls 之前，保证它先于 router 的同名 list 路由命中。
#
#    `batch-rules/preview|apply|recalc` 走 ViewSet 的 @action(detail=False)，
#    DRF 的 SimpleRouter 把「列表级动态路由」排在详情路由**之前**
#    （见 rest_framework/routers.py 的 routes 顺序：list → DynamicRoute(detail=False)
#    → detail），因此不会被 pk 正则抢匹配，无需额外 path。
urlpatterns = [
    path(
        'batch-naming/',
        BatchNamingViewSet.as_view({'get': 'list', 'put': 'update'}),
        name='campus-batch-naming-singleton',
    ),
] + router.urls
