"""Candidate URL Routing"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CandidateTagViewSet, CandidateViewSet

# 2026-06-29 花无缺: router prefix 改 r'' (config/urls.py 用了 path('candidates/') 挂载,
#   旧 router.register(r'candidates') 会双层 → /candidates/candidates/ → FE /candidates 404.
#   改成 r'' 让最终 path = /api/v1/candidates/ (单层, FE 直接命中)
router = DefaultRouter()
router.register(r'', CandidateViewSet, basename='candidate')
router.register(r'tags', CandidateTagViewSet, basename='candidate-tag')  # 顺便去掉 candidate- 前缀, 跟 /candidates/ 搭

urlpatterns = [
    path('', include(router.urls)),
]
