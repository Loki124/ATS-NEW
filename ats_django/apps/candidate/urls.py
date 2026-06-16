"""Candidate URL Routing"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CandidateTagViewSet, CandidateViewSet

router = DefaultRouter()
router.register(r'candidates', CandidateViewSet, basename='candidate')
router.register(r'candidate-tags', CandidateTagViewSet, basename='candidate-tag')

urlpatterns = [
    path('', include(router.urls)),
]
