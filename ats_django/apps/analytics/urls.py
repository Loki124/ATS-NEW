"""Analytics URL Routes - /api/v1/analytics/..."""
from rest_framework.routers import DefaultRouter

from .views import ExportTaskViewSet, ReportSnapshotViewSet

router = DefaultRouter()
router.register(r'reports', ReportSnapshotViewSet, basename='report-snapshot')
router.register(r'exports', ExportTaskViewSet, basename='export-task')

urlpatterns = router.urls
