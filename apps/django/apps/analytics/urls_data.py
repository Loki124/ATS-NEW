"""数据中心路由 - /api/v1/data/...  (G35 KPI + 订阅 + 通用导出)

FE web/app/src/api/data.ts 调:
  GET  /api/v1/data/kpi/                       KpiViewSet.list
  GET  /api/v1/data/subscriptions/             DataSubscriptionViewSet.list
  POST /api/v1/data/subscriptions/             DataSubscriptionViewSet.create
  DEL  /api/v1/data/subscriptions/<pk>/        DataSubscriptionViewSet.destroy (软删)
  GET  /api/v1/data/export/<resource>/         DataExportView (CSV/JSON, UTF-8 BOM, Field ACL)
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import KpiViewSet, DataSubscriptionViewSet
from .views_export import DataExportView

router = DefaultRouter()
router.register(r'kpi', KpiViewSet, basename='kpi')
router.register(r'subscriptions', DataSubscriptionViewSet, basename='subscription')

urlpatterns = router.urls + [
    # 资源导出（单 endpoint, 不走 router — resource 路由变量)
    # 资源白名单: Candidate / Demand / Position / Offer / Interview / Onboarding
    # 详 views_export.RESOURCE_ITER
    path('export/<str:resource>/', DataExportView.as_view(), name='data-export'),
]
