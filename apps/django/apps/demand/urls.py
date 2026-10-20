"""Demand URL Routes - /api/v1/demands/..."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DemandViewSet, DemandBatchUpdatePeopleView

router = DefaultRouter()
router.register(r'', DemandViewSet, basename='demand')

# 2026-10-20 S8-02: 批量变更需求人员 专属守卫端点。须排在 router.urls 之前,
# 否则会被 DemandViewSet 的 <pk> 路由截走 (pk 段 [^/.]+ 会吞掉 batch-update-people)。
urlpatterns = [
    path('batch-update-people/', DemandBatchUpdatePeopleView.as_view(), name='demand-batch-update-people'),
] + router.urls
