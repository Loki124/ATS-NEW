"""指标库路由 —— 挂在 /api/v1/metrics/ 下。

路由顺序注意：catalog 类固定路径必须排在 router 的 <pk> 详情路由之前，
否则会被 /templates/{pk}/ 之类的详情路由抢先匹配（项目既有踩坑经验）。
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AtomicMetricViewSet,
    CandidateFieldCatalogView,
    CandidateSnapshotView,
    DerivedFuncCatalogView,
    DerivedMetricViewSet,
    MetricTemplateViewSet,
    OperatorCatalogView,
    RuleExecuteView,
    sample_data,
)

app_name = 'metrics'

router = DefaultRouter()
router.register(r'atomic-metrics', AtomicMetricViewSet, basename='atomic-metric')
router.register(r'derived-metrics', DerivedMetricViewSet, basename='derived-metric')
router.register(r'templates', MetricTemplateViewSet, basename='metric-template')

urlpatterns = [
    # 目录与执行（固定路径，先于 router）
    path('operators/', OperatorCatalogView.as_view(), name='operator-catalog'),
    path('derived-funcs/', DerivedFuncCatalogView.as_view(), name='derived-func-catalog'),
    path('sample-data/', sample_data, name='sample-data'),
    path('candidate-fields/', CandidateFieldCatalogView.as_view(), name='candidate-field-catalog'),
    path('candidates/<str:candidate_id>/snapshot/', CandidateSnapshotView.as_view(), name='candidate-snapshot'),
    path('rules/execute/', RuleExecuteView.as_view(), name='rule-execute'),
    path('', include(router.urls)),
]
