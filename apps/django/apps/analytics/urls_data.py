"""数据中心路由 - /api/v1/data/...  (G35 KPI + 订阅)

FE web/app/src/api/data.ts 调:
  GET  /api/v1/data/kpi/                KpiViewSet.list
  GET  /api/v1/data/subscriptions/      DataSubscriptionViewSet.list
  POST /api/v1/data/subscriptions/      DataSubscriptionViewSet.create
  DEL  /api/v1/data/subscriptions/<pk>/ DataSubscriptionViewSet.destroy (软删)
"""
from rest_framework.routers import DefaultRouter

from .views import KpiViewSet, DataSubscriptionViewSet

router = DefaultRouter()
router.register(r'kpi', KpiViewSet, basename='kpi')
router.register(r'subscriptions', DataSubscriptionViewSet, basename='subscription')

urlpatterns = router.urls
