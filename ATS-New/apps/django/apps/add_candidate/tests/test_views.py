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


@pytest.mark.django_db
class TestParseStatusView:
    """GET /parse-status/{job_id}/ 测试"""

    def test_get_processing_job(self, api_client, hr_user):
        from apps.add_candidate.models import ParseJob
        job = ParseJob.objects.create(
            job_id='test_001', file_name='r.pdf', file_path='/tmp/r.pdf',
            file_size=1000, status='processing', phase='parsing', progress=50,
            actor=hr_user,
        )
        response = api_client.get('/api/v1/candidates/add-candidate/parse-status/test_001/')
        assert response.status_code == 200
        data = response.json()
        assert data['draft_id'] == job.draft_id
        assert data['status'] == 'processing'
        assert data['progress'] == 50

    def test_get_nonexistent_job_404(self, api_client):
        response = api_client.get('/api/v1/candidates/add-candidate/parse-status/nonexistent/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestDuplicateCheckView:
    """POST /duplicate-check/ 测试"""

    def test_duplicate_check_clean(self, api_client):
        """新候选人 → status=clean"""
        response = api_client.post(
            '/api/v1/candidates/add-candidate/duplicate-check/',
            {'draft_id': 'd1', 'phone': '13900000000', 'email': 'new@x.com', 'name': '新'},
            format='json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'clean'

    def test_duplicate_check_occupied(self, api_client, candidate_with_active_app):
        """已有 active application 的候选人 → status=occupied"""
        response = api_client.post(
            '/api/v1/candidates/add-candidate/duplicate-check/',
            {'draft_id': 'd1', 'phone': candidate_with_active_app.phone, 'email': '', 'name': ''},
            format='json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'occupied'


@pytest.mark.django_db
class TestReplaceFileView:
    """POST /replace-file/{draft_id}/ 测试"""

    def test_replace_success(self, api_client, hr_user, mock_parse_task):
        from apps.add_candidate.models import ParseJob
        ParseJob.objects.create(
            job_id='old_001', draft_id='d_replace',
            file_name='old.pdf', file_path='/tmp/old.pdf', file_size=100, actor=hr_user,
        )
        file = SimpleUploadedFile('new.pdf', b'%PDF-1.4 new', content_type='application/pdf')

        response = api_client.post(
            '/api/v1/candidates/add-candidate/replace-file/d_replace/',
            {'file': file},
            format='multipart',
        )
        assert response.status_code == 202
        assert 'new_job_id' in response.json()
        assert mock_parse_task.call_count == 1

    def test_replace_draft_not_found(self, api_client, mock_parse_task):
        file = SimpleUploadedFile('new.pdf', b'%PDF-1.4', content_type='application/pdf')
        response = api_client.post(
            '/api/v1/candidates/add-candidate/replace-file/nonexistent/',
            {'file': file},
            format='multipart',
        )
        assert response.status_code == 404
        assert mock_parse_task.call_count == 0


@pytest.mark.django_db
class TestBulkCreateView:
    """POST /bulk-create/ 测试"""

    @pytest.fixture
    def mock_score_task(self):
        """Mock score_batch_task.delay 避免真连 Redis

        score_batch_task 在 views.py 模块顶部导入，所以 patch 必须打在
        视图模块（apps.add_candidate.views），不是源模块 tasks。

        必须显式设置 .return_value.id 为字符串 — 否则默认 MagicMock 在
        DRF JSONRenderer 编码时触发 tolist() 无限递归（numpy 数组启发式判断）。
        """
        with patch('apps.add_candidate.views.score_batch_task.delay') as mock:
            mock.return_value.id = 'mock_task_id_001'
            yield mock

    @pytest.fixture
    def parsed_job_pending(self, db, hr_user):
        """1 个 pending draft 对应的已解析 ParseJob"""
        from apps.add_candidate.models import ParseJob
        return ParseJob.objects.create(
            job_id='job_bulk_001',
            draft_id='d1',
            file_name='r.pdf',
            file_path='/tmp/r.pdf',
            file_size=1000,
            status='done',
            parsed_data={
                'name': '张三',
                'phone': '13800138001',
                'email': 'zhang@test.com',
            },
            actor=hr_user,
        )

    def test_bulk_create_pending(self, api_client, parsed_job_pending, mock_score_task):
        """1 个 pending draft → 200 + task_id"""
        response = api_client.post(
            '/api/v1/candidates/add-candidate/bulk-create/',
            {
                'drafts': [
                    {
                        'draft_id': 'd1',
                        'direction': 'pending',
                        'channel': '招聘网站',
                        'source': 'Boss',
                        'provider': '',
                    }
                ],
                'submit_mode': 'async',
            },
            format='json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'task_id' in data
        assert len(data['created_candidate_ids']) == 1
        assert data['route'] == {'d1': 'pending'}
        assert mock_score_task.call_count == 1

    def test_bulk_create_position_requires_position_id(self, api_client, mock_score_task):
        """direction=position 但无 position_id → 400"""
        # 先建一个解析好的 job，避免 DRAFT_NOT_FOUND 误报
        from apps.add_candidate.models import ParseJob
        ParseJob.objects.create(
            job_id='job_bulk_pos', draft_id='d1',
            file_name='r.pdf', file_path='/tmp/r.pdf', file_size=1000,
            status='done',
            parsed_data={'name': '李四', 'phone': '13800138002', 'email': 'li@test.com'},
        )

        response = api_client.post(
            '/api/v1/candidates/add-candidate/bulk-create/',
            {
                'drafts': [
                    {
                        'draft_id': 'd1',
                        'direction': 'position',
                        'position_id': None,
                    }
                ],
                'submit_mode': 'async',
            },
            format='json',
        )
        assert response.status_code == 400
        assert mock_score_task.call_count == 0

    def test_bulk_create_rollback_on_partial_failure(self, api_client, mock_score_task):
        """第二个 draft 失败 → 第一个回滚"""
        from apps.add_candidate.models import ParseJob
        # 第一个 draft：合法 pending（带解析数据）
        ParseJob.objects.create(
            job_id='job_bulk_rb_1', draft_id='d1',
            file_name='r.pdf', file_path='/tmp/r1.pdf', file_size=1000,
            status='done',
            parsed_data={'name': '王五', 'phone': '13800138003', 'email': 'wang@test.com'},
        )
        # 第二个 draft：position 但缺 position_id（无 ParseJob 也行 — 校验在 service 层）

        response = api_client.post(
            '/api/v1/candidates/add-candidate/bulk-create/',
            {
                'drafts': [
                    {'draft_id': 'd1', 'direction': 'pending'},
                    {'draft_id': 'd2', 'direction': 'position', 'position_id': None},
                ],
                'submit_mode': 'async',
            },
            format='json',
        )
        assert response.status_code == 400
        from apps.candidate.models import Candidate
        # 第一个 draft 不应留下记录（事务回滚）
        assert Candidate.objects.count() == 0
        # score_batch_task 不应被调用（创建失败，未到评分）
        assert mock_score_task.call_count == 0
