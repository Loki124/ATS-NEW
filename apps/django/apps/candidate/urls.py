"""Candidate URL Routing - 2026-07-01: tags 改成显式 path 避免被 r'' 吃"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CandidateTagViewSet, CandidateViewSet, CandidateResumeFieldsView

# config/urls.py: path('candidates/', include(...))
# 之前 r'tags' + r'' 顺序错位: GET /candidates/tags/ 走到 CandidateViewSet
# 把 pk 当 'tags' 查 → 404. 改成显式 path 放 router.urls 前面.
#
# 2026-07-01: candidate ViewSet 加 2 个 detail=False action:
#   - status-details/schema (GET)
#   - merge (POST, 已存在)
# 2 个 detail=True action:
#   - status-details (PUT/PATCH)
#   - transition (POST, 已存在)
# 这些都通过 r'' router 自动暴露.

router = DefaultRouter()
router.register(r'', CandidateViewSet, basename='candidate')
# 不再 register r'tags', 改用显式 path 让 GET /candidates/tags/ 走到 CandidateTagViewSet.list

candidate_tags_list = CandidateTagViewSet.as_view({'get': 'list', 'post': 'create'})
candidate_tags_detail = CandidateTagViewSet.as_view({
    'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
})

urlpatterns = [
    path('tags/', candidate_tags_list, name='candidate-tag-list'),
    path('tags/<str:pk>/', candidate_tags_detail, name='candidate-tag-detail'),
    path('<str:pk>/resume-fields/', CandidateResumeFieldsView.as_view(), name='candidate-resume-fields'),
] + list(router.urls)
