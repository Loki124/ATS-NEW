"""Analytics URL Routes - /api/v1/analytics/...

路由布局：
- /api/v1/analytics/                              ReportSnapshotViewSet (报表快照)
- /api/v1/analytics/<pk>/                         ReportSnapshotViewSet
- /api/v1/analytics/exports/                      ExportTaskViewSet     (导出任务)
- /api/v1/analytics/exports/<pk>/                 ExportTaskViewSet
- /api/v1/analytics/exports/dashboard-summary/    ExportTaskViewSet.dashboard_summary
- /api/v1/analytics/exports/<pk>/run/             ExportTaskViewSet.run_task

⚠️ 修复记录 (2026-08-06 寇豆码): 原实现两个 ViewSet 都 register(r'')，
ExportTaskViewSet 的 list/detail/dashboard-summary 路由被先注册的
ReportSnapshotViewSet 完全吃掉 → 不可达。子资源前缀 `exports` 必须先于 r'' 注册。
"""
from rest_framework.routers import DefaultRouter

from .views import ExportTaskViewSet, ReportSnapshotViewSet

router = DefaultRouter()
# 子资源前缀必须先注册：否则被 r'' 的 `^(?P<pk>[^/.]+)/$` 当 pk='exports' 吃掉
router.register(r'exports', ExportTaskViewSet, basename='export-task')
router.register(r'', ReportSnapshotViewSet, basename='report-snapshot')

urlpatterns = router.urls
