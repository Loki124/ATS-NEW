"""Add Candidate V2 - URL routing tests

Phase 2 Task 1：验证 7 个 endpoint 都能被 Django URL dispatcher 正确解析到对应的 view class。

注意：
- 这里只测 URL resolve 正确性，不测业务逻辑。
- views 是占位 APIView（class XxxView(APIView): pass），所以不发起真实 HTTP 请求，
  避免被 IsAuthenticated 401 干扰。
- 完整 namespace 路径为 v1:add_candidate（v1 在 config/urls.py 中包裹）。
"""
import pytest
from django.urls import resolve, reverse

# 完整 namespace 路径（v1 在 config/urls.py 中包裹）
MOUNT = 'v1:add_candidate'


class TestAddCandidateURLs:
    """验证 7 个 endpoint 的 URL 解析。"""

    def test_upload_and_parse_url_resolves(self):
        """POST /api/v1/candidates/add-candidate/upload-and-parse/"""
        url = reverse(f'{MOUNT}:upload-and-parse')
        match = resolve(url)
        assert match.url_name == 'upload-and-parse'
        assert match.func.view_class.__name__ == 'UploadAndParseView'

    def test_parse_status_url_resolves(self):
        """GET /api/v1/candidates/add-candidate/parse-status/<job_id>/"""
        url = reverse(f'{MOUNT}:parse-status', kwargs={'job_id': 'job-001'})
        match = resolve(url)
        assert match.url_name == 'parse-status'
        assert match.func.view_class.__name__ == 'ParseStatusView'
        assert match.kwargs['job_id'] == 'job-001'

    def test_duplicate_check_url_resolves(self):
        """POST /api/v1/candidates/add-candidate/duplicate-check/"""
        url = reverse(f'{MOUNT}:duplicate-check')
        match = resolve(url)
        assert match.url_name == 'duplicate-check'
        assert match.func.view_class.__name__ == 'DuplicateCheckView'

    def test_replace_file_url_resolves(self):
        """POST /api/v1/candidates/add-candidate/replace-file/<draft_id>/"""
        url = reverse(f'{MOUNT}:replace-file', kwargs={'draft_id': 'draft-001'})
        match = resolve(url)
        assert match.url_name == 'replace-file'
        assert match.func.view_class.__name__ == 'ReplaceFileView'
        assert match.kwargs['draft_id'] == 'draft-001'

    def test_bulk_create_url_resolves(self):
        """POST /api/v1/candidates/add-candidate/bulk-create/"""
        url = reverse(f'{MOUNT}:bulk-create')
        match = resolve(url)
        assert match.url_name == 'bulk-create'
        assert match.func.view_class.__name__ == 'BulkCreateView'

    def test_scoring_start_url_resolves(self):
        """POST /api/v1/candidates/add-candidate/scoring/start/"""
        url = reverse(f'{MOUNT}:scoring-start')
        match = resolve(url)
        assert match.url_name == 'scoring-start'
        assert match.func.view_class.__name__ == 'ScoringStartView'

    def test_scoring_stream_url_resolves(self):
        """GET /api/v1/candidates/add-candidate/scoring/stream/<task_id>/"""
        url = reverse(f'{MOUNT}:scoring-stream', kwargs={'task_id': 'task-001'})
        match = resolve(url)
        assert match.url_name == 'scoring-stream'
        assert match.func.view_class.__name__ == 'ScoringStreamView'
        assert match.kwargs['task_id'] == 'task-001'
