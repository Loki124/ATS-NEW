"""职务管理路由 — /api/v1/position-titles/。"""
from rest_framework.routers import DefaultRouter

from .views import JobTitleViewSet

router = DefaultRouter()
router.register(r'', JobTitleViewSet, basename='position-title')

urlpatterns = router.urls
