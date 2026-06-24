"""Views 集成测试 - Phase 2

Task 2 覆盖 UploadAndParseView 的 3 个分支：
1. 合法 PDF 上传 → 202 + job_id
2. 非白名单文件（.exe）→ 400
3. 未登录请求 → 401/403
"""
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient


@pytest.fixture
def api_client(hr_user):
    """HR 角色登录的 API 客户端"""
    client = APIClient()
    client.force_authenticate(user=hr_user)
    return client


@pytest.fixture
def plain_client():
    """未认证的 API 客户端"""
    return APIClient()


@pytest.fixture
def mock_parse_task():
    """Mock parse_resume_task.delay 避免真连 Redis（task_always_eager 未传递到 Celery default app）"""
    with patch('apps.add_candidate.views.parse_resume_task.delay') as mock:
        yield mock


@pytest.mark.django_db
class TestUploadAndParseView:
    """POST /upload-and-parse/ 测试"""

    def test_upload_single_pdf_success(self, api_client, mock_parse_task):
        """上传 1 份 PDF → 202 + job_id"""
        file = SimpleUploadedFile(
            'test.pdf', b'%PDF-1.4 fake', content_type='application/pdf'
        )
        response = api_client.post(
            '/api/v1/candidates/add-candidate/upload-and-parse/',
            {'files': [file]},
            format='multipart',
        )
        assert response.status_code == 202
        data = response.json()
        assert 'job_ids' in data
        assert 'draft_ids' in data
        assert len(data['job_ids']) == 1
        assert len(data['draft_ids']) == 1
        assert mock_parse_task.call_count == 1

    def test_upload_rejects_non_whitelist(self, api_client, mock_parse_task):
        """上传 .exe → 400"""
        file = SimpleUploadedFile(
            'evil.exe', b'MZ\x90\x00', content_type='application/octet-stream'
        )
        response = api_client.post(
            '/api/v1/candidates/add-candidate/upload-and-parse/',
            {'files': [file]},
            format='multipart',
        )
        assert response.status_code == 400
        assert mock_parse_task.call_count == 0

    def test_upload_requires_auth(self, plain_client, mock_parse_task):
        """未登录 → 401/403"""
        file = SimpleUploadedFile(
            'test.pdf', b'%PDF-1.4', content_type='application/pdf'
        )
        response = plain_client.post(
            '/api/v1/candidates/add-candidate/upload-and-parse/',
            {'files': [file]},
            format='multipart',
        )
        # 401 或 403 都可以（取决于 IsHROrAbove 优先级）
        assert response.status_code in (401, 403)
        assert mock_parse_task.call_count == 0
