"""library URLs - 2026-06-29 简化版: 用 DRF router 配 r'' prefix (避免双层)"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SchoolViewSet, CompanyViewSet

# config/urls.py 挂载 path('library/', include(...))
# 这里 router r'' 让最终 path = /api/v1/library/schools/
# (双层会导致 /api/v1/library/schools/schools/ 404)
router = DefaultRouter()
router.register(r'schools', SchoolViewSet, basename='school')
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = [
    path('', include(router.urls)),
]
