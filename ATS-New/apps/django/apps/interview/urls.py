"""Interview URL Routes - /api/v1/interviews/..."""
from rest_framework.routers import DefaultRouter

from .views import InterviewEvaluationViewSet, InterviewViewSet

router = DefaultRouter()
router.register(r'', InterviewViewSet, basename='interview')
router.register(r'evaluations', InterviewEvaluationViewSet, basename='interview-evaluation')

urlpatterns = router.urls
