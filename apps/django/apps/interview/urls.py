"""Interview URL Routes - /api/v1/interviews/...

路由布局：
- /api/v1/interviews/                   InterviewViewSet           (面试)
- /api/v1/interviews/<pk>/              InterviewViewSet
- /api/v1/interviews/evaluations/       InterviewEvaluationViewSet (面试评价)
- /api/v1/interviews/evaluations/<pk>/  InterviewEvaluationViewSet

⚠️ 修复记录 (2026-08-06 寇豆码): 原实现两个 ViewSet 都 register(r'')，
InterviewEvaluationViewSet 的 list/detail 路由被先注册的 InterviewViewSet 吃掉 → 不可达。
子资源前缀 `evaluations` 必须先于 r'' 注册。
"""
from rest_framework.routers import DefaultRouter

from .views import InterviewEvaluationViewSet, InterviewViewSet

router = DefaultRouter()
# 子资源前缀必须先注册：否则被 r'' 的 `^(?P<pk>[^/.]+)/$` 当 pk='evaluations' 吃掉
router.register(r'evaluations', InterviewEvaluationViewSet, basename='interview-evaluation')
router.register(r'', InterviewViewSet, basename='interview')

urlpatterns = router.urls
