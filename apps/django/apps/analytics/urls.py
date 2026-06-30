"""Analytics URL Routes - /api/v1/analytics/..."""
from rest_framework.routers import DefaultRouter

from .views import ExportTaskViewSet, ReportSnapshotViewSet

router = DefaultRouter()
router.register(r'', ReportSnapshotViewSet, basename='report-snapshot')
router.register(r'', ExportTaskViewSet, basename='export-task')

urlpatterns = router.urls
