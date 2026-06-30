"""duplicate_check URLs — 2026-06-29.

FE api:
  POST /duplicate-check/check
  POST /duplicate-check/ocr-parse
"""
from django.urls import path
from .views import DuplicateCheckViewSet

check_view = DuplicateCheckViewSet.as_view({'post': 'check'})
ocr_view = DuplicateCheckViewSet.as_view({'post': 'ocr_parse'})

urlpatterns = [
    path('check', check_view, name='duplicate-check'),
    path('check/', check_view),
    path('ocr-parse', ocr_view, name='duplicate-check-ocr-parse'),
    path('ocr-parse/', ocr_view),
]
