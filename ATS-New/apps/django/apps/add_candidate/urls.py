"""Add Candidate V2 URL Routes

挂载点：/api/v1/candidates/add-candidate/  (config/urls.py)

7 个 endpoint：
- POST   upload-and-parse/                 UploadAndParseView
- GET    parse-status/<str:job_id>/        ParseStatusView
- POST   duplicate-check/                  DuplicateCheckView
- POST   replace-file/<str:draft_id>/      ReplaceFileView
- POST   bulk-create/                      BulkCreateView
- POST   scoring/start/                    ScoringStartView
- GET    scoring/stream/<str:task_id>/     ScoringStreamView (SSE)
"""
from django.urls import path

from .views import (
    BulkCreateView,
    DuplicateCheckView,
    ParseStatusView,
    ReplaceFileView,
    ScoringStartView,
    ScoringStreamView,
    UploadAndParseView,
)

app_name = 'add_candidate'

urlpatterns = [
    # Step 1: 上传解析 + 查重
    path('upload-and-parse/', UploadAndParseView.as_view(), name='upload-and-parse'),
    path('parse-status/<str:job_id>/', ParseStatusView.as_view(), name='parse-status'),
    path('duplicate-check/', DuplicateCheckView.as_view(), name='duplicate-check'),
    path('replace-file/<str:draft_id>/', ReplaceFileView.as_view(), name='replace-file'),

    # Step 2-3: 批量提交 + 评分
    path('bulk-create/', BulkCreateView.as_view(), name='bulk-create'),
    path('scoring/start/', ScoringStartView.as_view(), name='scoring-start'),
    path('scoring/stream/<str:task_id>/', ScoringStreamView.as_view(), name='scoring-stream'),
]
