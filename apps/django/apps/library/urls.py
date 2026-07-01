"""library URLs - 2026-07-01: 恢复 ModelViewSet 真实 CRUD (migrate 已跑过)"""
from rest_framework.routers import DefaultRouter

from .views import SchoolViewSet, CompanyViewSet

# config/urls.py: path('library/', include(...))
# 真实 ModelViewSet 连 library_school / library_company 表
router = DefaultRouter()
router.register(r'schools', SchoolViewSet, basename='school')
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = router.urls
