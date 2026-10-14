"""职级管理路由。

四个平级资源 (与设计 §3.3 端点表一致):
- ``job-levels/``                 职级 CRUD
- ``job-level-categories/``        职级类别 CRUD (含 job_level_count)
- ``job-level-grade-settings/``    职等上限单例 (``/current/``)
- ``job-level-sequences/``         职级序列开关单例 (``/current/``)
"""
from rest_framework.routers import DefaultRouter

from .views import (
    JobLevelCategoryViewSet,
    JobLevelGradeSettingViewSet,
    JobLevelSequenceViewSet,
    JobLevelViewSet,
)

router = DefaultRouter()
router.register(r'job-levels', JobLevelViewSet, basename='job-level')
router.register(r'job-level-categories', JobLevelCategoryViewSet, basename='job-level-category')
router.register(
    r'job-level-grade-settings', JobLevelGradeSettingViewSet, basename='job-level-grade-setting',
)
router.register(r'job-level-sequences', JobLevelSequenceViewSet, basename='job-level-sequence')

urlpatterns = router.urls
