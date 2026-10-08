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
    EvaluateSceneView,
    FilterAsyncView,
    FilterBySceneView,
    FilterStatusView,
    MetricDefinitionViewSet,
    MetricRuleViewSet,
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
# 持久化规则（CRUD + toggle/run）。注意：'rules/execute/' 是字面路径，
# 已排在 include(router.urls) 之前，故不会被 rules/{pk}/ 详情路由抢走。
router.register(r'rules', MetricRuleViewSet, basename='metric-rule')

urlpatterns = [
    # 目录与执行（固定路径，先于 router）
    path('operators/', OperatorCatalogView.as_view(), name='operator-catalog'),
    path('derived-funcs/', DerivedFuncCatalogView.as_view(), name='derived-func-catalog'),
    path('sample-data/', sample_data, name='sample-data'),
    path('candidate-fields/', CandidateFieldCatalogView.as_view(), name='candidate-field-catalog'),
    path('definitions/', MetricDefinitionViewSet.as_view(), name='metric-definition'),
    path('candidates/<str:candidate_id>/snapshot/', CandidateSnapshotView.as_view(), name='candidate-snapshot'),
    path('rules/execute/', RuleExecuteView.as_view(), name='rule-execute'),
    # 业务触发点：入池 / 筛选 / 评分 调用（字面路径先于 rules/{pk}/ 详情路由）
    path('rules/evaluate-scene/', EvaluateSceneView.as_view(), name='evaluate-scene'),
    path('rules/filter/', FilterBySceneView.as_view(), name='filter-by-scene'),
    # 全量异步筛选（候选人超过同步扫描上限时使用）+ 进度查询
    path('rules/filter-async/', FilterAsyncView.as_view(), name='filter-async'),
    path('rules/filter-status/', FilterStatusView.as_view(), name='filter-status'),
    path('', include(router.urls)),
]
