"""library URLs - 2026-07-01: 恢复 ModelViewSet 真实 CRUD (migrate 已跑过)"""
from rest_framework.routers import DefaultRouter

from .views import CompanyViewSet, MajorViewSet, SchoolViewSet

# config/urls.py: path('library/', include(...))
# 真实 ModelViewSet 连 library_school / library_company 表
router = DefaultRouter()
router.register(r'schools', SchoolViewSet, basename='school')
router.register(r'companies', CompanyViewSet, basename='company')
# 专业库（阳光高考专业库导入数据），院校库「专业」Tab 数据源
router.register(r'majors', MajorViewSet, basename='major')

urlpatterns = router.urls
