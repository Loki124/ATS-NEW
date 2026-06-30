"""library URLs - 2026-06-29 简化版: 用 DRF router"""
from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import SchoolViewSet, CompanyViewSet

# config/urls.py 挂载 path('library/', include(...))
# 这里 router r'' + urlpatterns = router.urls 直接挂.
# DRF router 第一条是 list 路由 r'^$', Django path() 编译后整体 regex = '^library/$'
# (单层, 不像 path('', include(router.urls)) 会引入双 ^ 永不 match)
router = DefaultRouter()
router.register(r'schools', SchoolViewSet, basename='school')
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = list(router.urls)
