"""校招定岗与结算路由（挂在 /api/v1/campus-placement/ 下）。

端点（契约 §4.3）：
  CRUD   /position-demands/            岗位需求（?need_status=&scope_type=&dept=）
  POST   /position-demands/{id}/review/    需求审核（approve / reject）
  POST   /position-demands/{id}/open/      开放 / 关闭报名
  POST   /position-demands/{id}/withdraw/  HRBP 撤回需求
  POST   /position-demands/{id}/publish/   发布需求
  CRUD   /applications/               志愿（?person=&batch=&status=）
  POST   /applications/               志愿填报（启动后拒绝）
  POST   /applications/{id}/push/     推送志愿给业务 BP
  POST   /applications/{id}/accept/   BP 录取（后续志愿自动释放）
  POST   /applications/{id}/reject/   BP 放弃（下一志愿自动推送 / 转人才市场）
  POST   /applications/{id}/assign/   指定分配（班主任 / 管理员）
  CRUD   /selection-flows/            撮合流程（POST = 启动）
  POST   /selection-flows/{id}/publish/    发布双选结果
  CRUD   /placement-records/ /placement-goals/ /placement-metrics/ /placement-assessments/
  CRUD   /price-schemes/ /price-bids/
  CRUD   /revenue-records/ /bills/
  GET    /settlement/stat/            收入统计
  GET    /settlement/price/           定价管理视图

⚠️ 自定义路径必须排在 **router.urls 之前**（与 `campus_rotation/urls.py` 同款约定）：
    DRF router 的详情路由 `^{prefix}/(?P<pk>[^/.]+)/` 能匹配任意子路径名，
    router.urls 在前会让自定义端点被详情路由抢先命中 → 404。
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BillViewSet,
    PlacementAssessmentViewSet,
    PlacementGoalViewSet,
    PlacementMetricViewSet,
    PlacementRecordViewSet,
    PositionApplicationViewSet,
    PositionDemandViewSet,
    PriceBidViewSet,
    PriceSchemeViewSet,
    RevenueRecordViewSet,
    SelectionFlowViewSet,
    SettlementPriceView,
    SettlementStatView,
)

router = DefaultRouter()
router.register(
    r'position-demands', PositionDemandViewSet, basename='campus-placement-demand',
)
router.register(
    r'applications', PositionApplicationViewSet, basename='campus-placement-application',
)
router.register(
    r'selection-flows', SelectionFlowViewSet, basename='campus-placement-selection-flow',
)
router.register(
    r'placement-records', PlacementRecordViewSet, basename='campus-placement-record',
)
router.register(
    r'placement-goals', PlacementGoalViewSet, basename='campus-placement-goal',
)
router.register(
    r'placement-metrics', PlacementMetricViewSet, basename='campus-placement-metric',
)
router.register(
    r'placement-assessments', PlacementAssessmentViewSet, basename='campus-placement-assessment',
)
router.register(
    r'price-schemes', PriceSchemeViewSet, basename='campus-placement-price-scheme',
)
router.register(
    r'price-bids', PriceBidViewSet, basename='campus-placement-price-bid',
)
router.register(
    r'revenue-records', RevenueRecordViewSet, basename='campus-placement-revenue-record',
)
router.register(
    r'bills', BillViewSet, basename='campus-placement-bill',
)

urlpatterns = [
    path(
        'settlement/stat/',
        SettlementStatView.as_view(),
        name='campus-placement-settlement-stat',
    ),
    path(
        'settlement/price/',
        SettlementPriceView.as_view(),
        name='campus-placement-settlement-price',
    ),
] + router.urls
