"""Candidate URL Routing"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CandidateTagViewSet, CandidateViewSet

# 2026-06-30 花无缺: 改用 router.urls 直接挂 (跟 invitation 一致).
#   之前 path('', include(router.urls)) 会让 DRF router 的 '^$' 变 '^/api/v1/candidates/^$'
#   (双 ^ 永不 match). 改成 urlpatterns = router.urls, DRF router 直接给 list path '',
#   Django path() 在 config/urls.py 用 path('candidates/', include(...)) 拼 prefix,
#   最终 path = '^/api/v1/candidates/$' (单 ^ 正确 match)
router = DefaultRouter()
router.register(r'', CandidateViewSet, basename='candidate')
router.register(r'tags', CandidateTagViewSet, basename='candidate-tag')

urlpatterns = router.urls
