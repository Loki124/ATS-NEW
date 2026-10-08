"""Views 集成测试 - Phase 2

Task 2 覆盖 UploadAndParseView 的 3 个分支：
1. 合法 PDF 上传 → 202 + job_id
2. 非白名单文件（.exe）→ 400
3. 未登录请求 → 401/403
"""
import json
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
        # 响应经 CamelCaseJSONRenderer 渲染 (settings.base:296)，键为 camelCase
        assert 'jobIds' in data
        assert 'draftIds' in data
        assert len(data['jobIds']) == 1
        assert len(data['draftIds']) == 1
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
        # 响应经 CamelCaseJSONRenderer 渲染，draft_id → draftId
        assert data['draftId'] == job.draft_id
        assert data['status'] == 'processing'
        assert data['progress'] == 50

    def test_get_nonexistent_job_404(self, api_client):
        response = api_client.get('/api/v1/candidates/add-candidate/parse-status/nonexistent/')
        assert response.status_code == 404

    def test_other_user_cannot_view_pii(self, db, hr_user):
        """I-6: 跨用户读 PII → 403"""
        from django.contrib.auth import get_user_model
        from apps.add_candidate.models import ParseJob
        from rest_framework.test import APIClient
        other = get_user_model().objects.create_user(
            username='other_hr', password='Test@1234', employee_id='E999',
            department=hr_user.department,
        )
        ParseJob.objects.create(
            job_id='p_001', file_name='r.pdf', file_path='/tmp/r.pdf',
            file_size=100, status='done', phase='done', progress=100,
            actor=hr_user, parsed_data={'name': '机密'},
        )
        client = APIClient()
        client.force_authenticate(user=other)
        response = client.get('/api/v1/candidates/add-candidate/parse-status/p_001/')
        assert response.status_code == 403

    def test_superuser_can_view_any_pii(self, db, hr_user, super_user):
        """I-6: superuser 豁免 actor 校验"""
        from apps.add_candidate.models import ParseJob
        ParseJob.objects.create(
            job_id='p_002', file_name='r.pdf', file_path='/tmp/r.pdf',
            file_size=100, status='done', phase='done', progress=100,
            actor=hr_user,
        )
        client = APIClient()
        client.force_authenticate(user=super_user)
        response = client.get('/api/v1/candidates/add-candidate/parse-status/p_002/')
        assert response.status_code == 200


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
        """I-7: ReplaceFile 复用 job_id/draft_id，原地更新 ParseJob（不 orphan 旧 draft）"""
        from apps.add_candidate.models import ParseJob
        ParseJob.objects.create(
            job_id='rpl_001', draft_id='d_replace',
            file_name='old.pdf', file_path='/tmp/old.pdf', file_size=100, actor=hr_user,
        )
        file = SimpleUploadedFile('new.pdf', b'%PDF-1.4 new', content_type='application/pdf')

        response = api_client.post(
            '/api/v1/candidates/add-candidate/replace-file/d_replace/',
            {'file': file},
            format='multipart',
        )
        assert response.status_code == 202
        data = response.json()
        # 响应经 CamelCaseJSONRenderer 渲染，job_id → jobId / draft_id → draftId
        assert data['jobId'] == 'rpl_001'  # SAME job_id (reused, not new)
        assert data['draftId'] == 'd_replace'
        # 原 ParseJob 原地更新（不是新插入一条）
        assert ParseJob.objects.filter(draft_id='d_replace').count() == 1
        job = ParseJob.objects.get(job_id='rpl_001')
        assert job.file_name == 'new.pdf'
        assert job.status == 'processing'
        assert mock_parse_task.call_count == 1
        mock_parse_task.assert_called_once_with('rpl_001')

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
        # 响应经 CamelCaseJSONRenderer 渲染；
        # 注意请求体里的 draft_id/submit_mode 是入参（CamelCaseJSONParser 兼容 snake_case），不改
        assert 'taskId' in data
        assert len(data['createdCandidateIds']) == 1
        # route 的 key 是 draft_id 值本身（数据不是字段名），渲染器不转换
        assert data['route'] == {'d1': 'pending'}
        assert mock_score_task.call_count == 1

    def test_bulk_create_position_requires_position_id(self, api_client, hr_user, mock_score_task):
        """direction=position 但无 position_id → 400"""
        # 先建一个归属当前用户的解析好的 job，避免 DRAFT_NOT_FOUND / FOREIGN_DRAFT 误报
        from apps.add_candidate.models import ParseJob
        ParseJob.objects.create(
            job_id='job_bulk_pos', draft_id='d1',
            file_name='r.pdf', file_path='/tmp/r.pdf', file_size=1000,
            status='done', actor=hr_user,
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

    def test_bulk_create_rollback_on_partial_failure(self, api_client, hr_user, mock_score_task):
        """第二个 draft 失败 → 第一个回滚"""
        from apps.add_candidate.models import ParseJob
        # 第一个 draft：合法 pending（带解析数据）
        ParseJob.objects.create(
            job_id='job_bulk_rb_1', draft_id='d1',
            file_name='r.pdf', file_path='/tmp/r1.pdf', file_size=1000,
            status='done', actor=hr_user,
            parsed_data={'name': '王五', 'phone': '13800138003', 'email': 'wang@test.com'},
        )
        # 第二个 draft：position 但缺 position_id —— 需归属当前用户的 ParseJob 才能通过
        # IDOR 校验进入 service 层做校验（无 ParseJob 会被视图层 FOREIGN_DRAFT 拦截返回 403）。
        ParseJob.objects.create(
            job_id='job_bulk_rb_2', draft_id='d2',
            file_name='r2.pdf', file_path='/tmp/r2.pdf', file_size=1000,
            status='done', actor=hr_user,
            parsed_data={'name': '赵六', 'phone': '13800138004', 'email': 'zhao@test.com'},
        )

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


@pytest.mark.django_db
class TestBulkCreateRecruitTypePassthrough:
    """候选人与需求/职位同根因 (2026-10-08): V2 批量创建须透传 request.recruit_type,
    否则落库默认 social, 在 campus 列表被硬分区过滤 → 新增候选人不显示。
    """

    @pytest.fixture
    def mock_score_task(self):
        with patch('apps.add_candidate.views.score_batch_task.delay') as mock:
            mock.return_value.id = 'mock_task_rt'
            yield mock

    @staticmethod
    def _list_ids(response):
        data = response.json()
        # StandardResultsSetPagination 经 success_response 包裹:
        # {success, data:{count, results, ...}, code, message}
        payload = data.get('data', data)
        items = payload.get('results') if isinstance(payload, dict) else payload
        return [it.get('id') for it in (items or [])]

    def test_campus_bulk_create_sets_recruit_type_and_partitions_list(
        self, api_client, hr_user, super_user, mock_score_task,
    ):
        from apps.add_candidate.models import ParseJob
        from apps.candidate.models import Candidate
        from rest_framework.test import APIClient

        ParseJob.objects.create(
            job_id='job_rt_1', draft_id='d_rt',
            file_name='r.pdf', file_path='/tmp/r.pdf', file_size=1000,
            status='done', actor=hr_user,
            parsed_data={'name': '校区张三', 'phone': '13800138051', 'email': 'rt@test.com'},
        )
        # 以 campus 系统上下文提交批量创建
        resp = api_client.post(
            '/api/v1/candidates/add-candidate/bulk-create/',
            {'drafts': [{'draft_id': 'd_rt', 'direction': 'pending'}], 'submit_mode': 'async'},
            format='json', HTTP_X_RECRUIT_TYPE='campus',
        )
        assert resp.status_code == 200
        cand = Candidate.objects.get(phone='13800138051')
        # 核心回归: recruit_type 须随请求上下文落 campus, 而非模型默认 social
        assert cand.recruit_type == 'campus'

        # 读侧硬分区: 超管按 recruit_type 过滤 (绕过部门/创建人 scope 噪声)
        admin = APIClient()
        admin.force_authenticate(user=super_user)
        camp = admin.get('/api/v1/candidates/', HTTP_X_RECRUIT_TYPE='campus')
        assert camp.status_code == 200
        assert cand.id in self._list_ids(camp)

        soc = admin.get('/api/v1/candidates/', HTTP_X_RECRUIT_TYPE='social')
        assert soc.status_code == 200
        assert cand.id not in self._list_ids(soc)


@pytest.mark.django_db
class TestManualCreateAndOverride:
    """POST /manual-create/ + bulk-create 覆盖（修复「手动字段被自动清理」）

    穿透真实 View 层（不走 unit 绕过 serializer/view）：
    - 手动录入数据经 manual-create 落 ParseJob，再经 bulk-create 落 Candidate
    - 简历解析值被手动编辑覆盖时，落库以编辑值为准（edited ?? parsed 合并链路）
    """

    @pytest.fixture
    def mock_score_task(self):
        with patch('apps.add_candidate.views.score_batch_task.delay') as mock:
            mock.return_value.id = 'mock_task_id_manual'
            yield mock

    def test_manual_create_returns_draft(self, api_client):
        """无文件手动建草稿 → 201 + parsed/duplicate 同构 parse-status"""
        response = api_client.post(
            '/api/v1/candidates/add-candidate/manual-create/',
            {'name': '手动张三', 'phone': '13912345678', 'email': 'manual@x.com',
             'gender': '男', 'age': 30},
            format='json',
        )
        assert response.status_code == 201
        data = response.json()
        # CamelCaseJSONRenderer: draft_id → draftId, job_id → jobId
        assert data['draftId']
        assert data['jobId']
        assert data['status'] == 'clean'  # 新手机号无人占用
        assert data['parsed']['name'] == '手动张三'
        assert data['parsed']['phone'] == '13912345678'
        assert data['parsed']['email'] == 'manual@x.com'
        # 落库 ParseJob（无文件，file_path='' file_size=0 status='done'）
        from apps.add_candidate.models import ParseJob
        job = ParseJob.objects.get(draft_id=data['draftId'])
        assert job.file_path == ''
        assert job.file_size == 0
        assert job.status == 'done'
        assert job.parsed_data['name'] == '手动张三'

    def test_manual_create_requires_fields(self, api_client):
        """name/phone/email 缺省 → 400"""
        response = api_client.post(
            '/api/v1/candidates/add-candidate/manual-create/',
            {'name': ''},
            format='json',
        )
        assert response.status_code == 400

    def test_bulk_create_persists_manual_data(self, api_client, mock_score_task):
        """核心回归：手动录入数据经 bulk-create 落库，未被清空"""
        resp = api_client.post(
            '/api/v1/candidates/add-candidate/manual-create/',
            {'name': '手动张三', 'phone': '13912345678', 'email': 'manual@x.com'},
            format='json',
        )
        draft_id = resp.json()['draftId']
        response = api_client.post(
            '/api/v1/candidates/add-candidate/bulk-create/',
            {
                'drafts': [
                    {
                        'draft_id': draft_id,
                        'direction': 'pending',
                        'parsed_data': {
                            'name': '手动张三', 'phone': '13912345678',
                            'email': 'manual@x.com', 'educations': [], 'experiences': [],
                            'confidence': 1.0,
                        },
                    }
                ],
                'submit_mode': 'async',
            },
            format='json',
        )
        assert response.status_code == 200
        from apps.candidate.models import Candidate
        cand = Candidate.objects.get(phone='13912345678')
        assert cand.name == '手动张三'      # 关键：手动值落库，未被清空
        assert cand.email == 'manual@x.com'

    def test_bulk_create_applies_edit_override(self, api_client, hr_user, mock_score_task):
        """简历解析值被手动编辑覆盖 → 落库以编辑值为准（edited ?? parsed 合并链路打通）"""
        from apps.add_candidate.models import ParseJob
        ParseJob.objects.create(
            job_id='job_edit_ov', draft_id='d_edit',
            file_name='r.pdf', file_path='/tmp/r.pdf', file_size=1000,
            status='done', actor=hr_user,
            parsed_data={'name': '解析李四', 'phone': '13800138099', 'email': 'parsed@x.com'},
        )
        # 前端合并 edited: name 改成「改后王五」，phone/email 保持解析值
        merged = {
            'name': '改后王五', 'phone': '13800138099', 'email': 'parsed@x.com',
            'educations': [], 'experiences': [], 'confidence': 0.9,
        }
        response = api_client.post(
            '/api/v1/candidates/add-candidate/bulk-create/',
            {
                'drafts': [{'draft_id': 'd_edit', 'direction': 'pending', 'parsed_data': merged}],
                'submit_mode': 'async',
            },
            format='json',
        )
        assert response.status_code == 200
        from apps.candidate.models import Candidate
        cand = Candidate.objects.get(phone='13800138099')
        assert cand.name == '改后王五'   # 覆盖生效，证明 edited 链路穿透到 DB


@pytest.mark.django_db
class TestScoringEndpoints:
    """Scoring Start + Stream 测试"""

    def test_scoring_start_returns_stream_url(self, api_client):
        from unittest.mock import patch, MagicMock
        with patch('apps.add_candidate.views.score_batch_task.delay') as mock_delay:
            mock_delay.return_value = MagicMock(id='task_xyz')
            response = api_client.post(
                '/api/v1/candidates/add-candidate/scoring/start/',
                {'candidate_ids': ['c1', 'c2'], 'task_id': 'task_test'},
                format='json',
            )
        assert response.status_code == 200
        data = response.json()
        # 响应经 CamelCaseJSONRenderer 渲染，stream_url → streamUrl
        # （上面请求体里的 task_id 是入参，保持 snake_case 不动）
        assert 'streamUrl' in data
        assert 'task_test' in data['streamUrl']

    def test_scoring_stream_returns_event_stream(self, api_client, hr_user):
        """I-4: SSE 改用 Redis pub/sub — test env 无 Redis，用 mock _get_redis 注入 fake pubsub

        I-6 (2026-07-02) 之后 ScoringStreamView.get 先做 IDOR 归属校验：
        读 redis key `add_candidate:scoring:owner:<task_id>`，None → 404，
        非当前用户 → 403。所以 fake redis 的 .get() 必须返回当前用户 id，
        否则 MagicMock 会被 str() 成 "<MagicMock ...>" 判定为他人 → 403。
        """
        from unittest.mock import patch, MagicMock
        fake_pubsub = MagicMock()
        fake_pubsub.listen.return_value = [
            {'type': 'message', 'data': json.dumps({'event': 'test', 'data': {'x': 1}})},
            {'type': 'message', 'data': json.dumps({'event': 'task-complete', 'data': {}})},
        ]
        with patch('apps.add_candidate.sse._get_redis') as mock_redis:
            mock_redis.return_value.get.return_value = str(hr_user.id).encode()
            mock_redis.return_value.pubsub.return_value = fake_pubsub
            response = api_client.get(
                '/api/v1/candidates/add-candidate/scoring/stream/sse_test_1/'
            )
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/event-stream'

    def test_scoring_stream_rejects_other_users_task(self, api_client):
        """I-6: task 归属他人 → 403（锁死 IDOR 修复，防回归）"""
        from unittest.mock import patch
        with patch('apps.add_candidate.sse._get_redis') as mock_redis:
            mock_redis.return_value.get.return_value = b'someone-else-user-id'
            response = api_client.get(
                '/api/v1/candidates/add-candidate/scoring/stream/sse_test_2/'
            )
        assert response.status_code == 403

    def test_scoring_stream_unknown_task_404(self, api_client):
        """I-6: owner key 不存在（任务不存在/已过期）→ 404"""
        from unittest.mock import patch
        with patch('apps.add_candidate.sse._get_redis') as mock_redis:
            mock_redis.return_value.get.return_value = None
            response = api_client.get(
                '/api/v1/candidates/add-candidate/scoring/stream/sse_test_3/'
            )
        assert response.status_code == 404

    def test_scoring_start_requires_auth(self, plain_client):
        response = plain_client.post(
            '/api/v1/candidates/add-candidate/scoring/start/',
            {'candidate_ids': ['c1'], 'task_id': 't1'},
            format='json',
        )
        assert response.status_code in (401, 403)
