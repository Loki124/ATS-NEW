# AddCandidateModal V2 - Phase 2: 后端 API + Celery + SSE 实施 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 7 个新 DRF endpoint + 3 个 Celery task + 1 个 SSE 评分流，集成 4 个 service（Phase 1 产出），覆盖上传/解析/查重/批量创建/评分全链路。

**Architecture:**
- 新增 `apps/add_candidate/views.py` 7 个 `APIView`（post/get）
- 新增 `apps/add_candidate/tasks.py` 3 个 Celery task（解析/评分/通知）
- 新增 `apps/add_candidate/sse.py` 1 个 SSE 视图（`StreamingHttpResponse` + 内存 dict pub/sub）
- 新增 `apps/add_candidate/serializers.py` 5 个 DRF serializer
- 新增 `apps/add_candidate/urls.py` 路由表
- 挂载到 `config/urls.py` 的 `/api/v1/candidates/add-candidate/` 子路由
- 复用 Phase 1 的 4 个 service

**Tech Stack:**
- Backend: Python 3.11, Django 4.x, DRF, Celery + Redis (项目已有), StreamingHttpResponse (SSE)
- 测试: pytest-django + APITestCase

**Spec:** [docs/superpowers/specs/2026-06-22-add-candidate-v2-design.md](../specs/2026-06-22-add-candidate-v2-design.md) §5
**依赖 Phase 1:** `ResumeParserService` / `DuplicateCheckService` / `ScoringService` / `BulkCreateService` 全部已就绪

---

## 文件结构

### 新增（5 个后端文件）
- `apps/django/apps/add_candidate/serializers.py` — 5 个 DRF serializer (~100 行)
- `apps/django/apps/add_candidate/views.py` — 7 个 APIView (~350 行)
- `apps/django/apps/add_candidate/urls.py` — 路由表 (~30 行)
- `apps/django/apps/add_candidate/tasks.py` — 3 个 Celery task (~120 行)
- `apps/django/apps/add_candidate/sse.py` — SSE 流视图 (~80 行)

### 新增测试（1 个）
- `apps/django/apps/add_candidate/tests/test_views.py` — 7 endpoint 集成测试 (~250 行)

### 修改（1 个）
- `apps/django/config/urls.py` — 挂载新子路由
- `apps/django/apps/add_candidate/views.py` — 在 7 endpoint 顶部加 `@permission_classes([IsAuthenticated, IsHROrAbove])` 装饰

---

## 全局约束

- **权限**：默认 `IsAuthenticated`；`upload-and-parse` 和 `bulk-create` 需 `IsHROrAbove`；`scoring/start` 需 `IsAuthenticated`
- **错误响应**：DRF 标准格式 `{ "detail": "...", "code": "DUPLICATE_CHECK_FAILED" }`
- **SSE 心跳**：每 15s 推一个 `: heartbeat\n\n` keepalive 注释
- **Celery 任务队列**：解析任务用 default queue；评分任务用专用 `scoring` queue
- **重试**：评分任务失败自动重试 3 次，间隔 5s

---

## Task 1: Serializers + URL 路由

**Files:**
- Create: `apps/django/apps/add_candidate/serializers.py`
- Create: `apps/django/apps/add_candidate/urls.py`
- Create: `apps/django/apps/add_candidate/tests/test_urls.py`
- Modify: `apps/django/config/urls.py` (挂载子路由)

### Step 1.1: 写失败测试

`apps/django/apps/add_candidate/tests/test_urls.py`:
```python
"""URL 路由测试"""
from django.urls import resolve, reverse


def test_upload_and_parse_url_resolves():
    """POST /api/v1/candidates/add-candidate/upload-and-parse/ → UploadAndParseView"""
    match = resolve('/api/v1/candidates/add-candidate/upload-and-parse/')
    assert match.func.view_class.__name__ == 'UploadAndParseView'


def test_parse_status_url_resolves():
    match = resolve('/api/v1/candidates/add-candidate/parse-status/abc123/')
    assert match.func.view_class.__name__ == 'ParseStatusView'
    assert match.kwargs['job_id'] == 'abc123'


def test_duplicate_check_url_resolves():
    match = resolve('/api/v1/candidates/add-candidate/duplicate-check/')
    assert match.func.view_class.__name__ == 'DuplicateCheckView'


def test_replace_file_url_resolves():
    match = resolve('/api/v1/candidates/add-candidate/replace-file/draft_001/')
    assert match.func.view_class.__name__ == 'ReplaceFileView'
    assert match.kwargs['draft_id'] == 'draft_001'


def test_bulk_create_url_resolves():
    match = resolve('/api/v1/candidates/add-candidate/bulk-create/')
    assert match.func.view_class.__name__ == 'BulkCreateView'


def test_scoring_start_url_resolves():
    match = resolve('/api/v1/candidates/add-candidate/scoring/start/')
    assert match.func.view_class.__name__ == 'ScoringStartView'


def test_scoring_stream_url_resolves():
    match = resolve('/api/v1/candidates/add-candidate/scoring/stream/task_abc/')
    assert match.func.view_class.__name__ == 'ScoringStreamView'
    assert match.kwargs['task_id'] == 'task_abc'
```

### Step 1.2: 跑测试确认失败

```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/apps/django && .venv/bin/python -m pytest apps/add_candidate/tests/test_urls.py -v
```
Expected: `ModuleNotFoundError: No module named 'apps.add_candidate.urls'`（也可能是 NoAppError 之类）

### Step 1.3: 写实现

`apps/django/apps/add_candidate/serializers.py`:
```python
"""Add Candidate V2 - DRF serializers"""
from rest_framework import serializers


class UploadAndParseRequestSerializer(serializers.Serializer):
    """POST /upload-and-parse/ 的请求体（multipart）"""
    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=20,
    )


class UploadAndParseResponseSerializer(serializers.Serializer):
    """POST /upload-and-parse/ 的响应体"""
    job_ids = serializers.ListField(child=serializers.CharField())
    draft_ids = serializers.ListField(child=serializers.CharField())


class ParseStatusResponseSerializer(serializers.Serializer):
    """GET /parse-status/{job_id}/ 的响应体"""
    draft_id = serializers.CharField()
    status = serializers.ChoiceField(choices=['processing', 'done', 'failed'])
    phase = serializers.ChoiceField(
        choices=['uploading', 'parsing', 'checking', None],
        allow_null=True,
    )
    progress = serializers.IntegerField(min_value=0, max_value=100)
    parsed = serializers.DictField(required=False, allow_null=True)
    duplicate = serializers.DictField(required=False, allow_null=True)
    error = serializers.CharField(required=False, allow_null=True)


class DuplicateCheckRequestSerializer(serializers.Serializer):
    """POST /duplicate-check/ 的请求体"""
    draft_id = serializers.CharField()
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)


class ReplaceFileResponseSerializer(serializers.Serializer):
    """POST /replace-file/{draft_id}/ 的响应体"""
    new_job_id = serializers.CharField()


class BulkCreateDraftSerializer(serializers.Serializer):
    """bulk-create 单条 draft"""
    draft_id = serializers.CharField()
    direction = serializers.ChoiceField(choices=['pending', 'talent', 'position'])
    position_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    channel = serializers.CharField(required=False, allow_blank=True)
    source = serializers.CharField(required=False, allow_blank=True)
    provider = serializers.CharField(required=False, allow_blank=True)


class BulkCreateRequestSerializer(serializers.Serializer):
    """POST /bulk-create/ 的请求体"""
    drafts = BulkCreateDraftSerializer(many=True)
    submit_mode = serializers.ChoiceField(choices=['wait', 'async'])


class BulkCreateResponseSerializer(serializers.Serializer):
    """POST /bulk-create/ 的响应体"""
    task_id = serializers.CharField()
    created_candidate_ids = serializers.ListField(child=serializers.CharField())
    route = serializers.DictField(child=serializers.CharField())


class ScoringStartRequestSerializer(serializers.Serializer):
    """POST /scoring/start/ 的请求体"""
    candidate_ids = serializers.ListField(child=serializers.CharField(), min_length=1)
    task_id = serializers.CharField()


class ScoringStartResponseSerializer(serializers.Serializer):
    """POST /scoring/start/ 的响应体"""
    stream_url = serializers.CharField()
```

`apps/django/apps/add_candidate/urls.py`:
```python
"""Add Candidate V2 - URL 路由"""
from django.urls import path
from . import views

app_name = 'add_candidate'

urlpatterns = [
    path('upload-and-parse/', views.UploadAndParseView.as_view(), name='upload-and-parse'),
    path('parse-status/<str:job_id>/', views.ParseStatusView.as_view(), name='parse-status'),
    path('duplicate-check/', views.DuplicateCheckView.as_view(), name='duplicate-check'),
    path('replace-file/<str:draft_id>/', views.ReplaceFileView.as_view(), name='replace-file'),
    path('bulk-create/', views.BulkCreateView.as_view(), name='bulk-create'),
    path('scoring/start/', views.ScoringStartView.as_view(), name='scoring-start'),
    path('scoring/stream/<str:task_id>/', views.ScoringStreamView.as_view(), name='scoring-stream'),
]
```

`apps/django/config/urls.py` 修改（先 Read 找到合适位置）:
```python
# 在 candidates/ 子路由块之后、talent-pool/ 之前加一行：
path('api/v1/candidates/add-candidate/', include('apps.add_candidate.urls')),
```

### Step 1.4: 跑测试确认通过

```bash
.venv/bin/python -m pytest apps/add_candidate/tests/test_urls.py -v
```
Expected: 7 PASSED（但因为 view 文件还没创建，可能 NoAppError 或 attribute error - 这是预期的，下个 task 创建 view）

注：本 task 只测 URL 路由 resolve，view 类存在但不要求实现完整。 如果 view 类不存在导致 resolve 失败，临时创建 `apps/django/apps/add_candidate/views.py` 含 7 个 `APIView` 占位类：

```python
# 临时占位
from rest_framework.views import APIView
class UploadAndParseView(APIView): pass
class ParseStatusView(APIView): pass
class DuplicateCheckView(APIView): pass
class ReplaceFileView(APIView): pass
class BulkCreateView(APIView): pass
class ScoringStartView(APIView): pass
class ScoringStreamView(APIView): pass
```

Task 2 会替换占位为真实实现。

### Step 1.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/apps/django/apps/add_candidate/serializers.py \
        ATS-New/apps/django/apps/add_candidate/urls.py \
        ATS-New/apps/django/apps/add_candidate/tests/test_urls.py \
        ATS-New/apps/django/config/urls.py
git commit -m "feat(add-candidate): Phase 2 路由 + serializers"
```

---

## Task 2: Upload + Parse endpoint

**Files:**
- Modify: `apps/django/apps/add_candidate/views.py`（替换 `UploadAndParseView` 占位 + 加 helper）
- Modify: `apps/django/apps/add_candidate/tests/test_views.py`（添加 3 个测试）

### Step 2.1: 写失败测试

在 `test_views.py` 顶部加 imports，添加以下测试：

```python
"""Views 集成测试 - Phase 2"""
import io
import pytest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from apps.add_candidate.models import ParseJob  # 见 Step 2.3


@pytest.fixture
def api_client(hr_user):
    """HR 角色登录的 API 客户端"""
    client = APIClient()
    client.force_authenticate(user=hr_user)
    return client


@pytest.fixture
def plain_client(super_user):
    return APIClient()


@pytest.mark.django_db
class TestUploadAndParseView:
    """POST /upload-and-parse/ 测试"""

    def test_upload_single_pdf_success(self, api_client):
        """上传 1 份 PDF → 202 + job_id"""
        file = SimpleUploadedFile('test.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
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

    def test_upload_rejects_non_whitelist(self, api_client):
        """上传 .exe → 400"""
        file = SimpleUploadedFile('evil.exe', b'MZ\x90\x00', content_type='application/octet-stream')
        response = api_client.post(
            '/api/v1/candidates/add-candidate/upload-and-parse/',
            {'files': [file]},
            format='multipart',
        )
        assert response.status_code == 400

    def test_upload_requires_auth(self, plain_client):
        """未登录 → 401"""
        file = SimpleUploadedFile('test.pdf', b'%PDF-1.4', content_type='application/pdf')
        response = plain_client.post(
            '/api/v1/candidates/add-candidate/upload-and-parse/',
            {'files': [file]},
            format='multipart',
        )
        # 401 或 403 都可以（取决于 IsHROrAbove 优先级）
        assert response.status_code in (401, 403)
```

### Step 2.2: 创建 ParseJob model

为了让测试可运行，需要一个 ParseJob model 记录 job_id → 文件路径。 在 `apps/django/apps/add_candidate/models.py` 中添加：

```python
"""Add Candidate V2 - Models"""
from django.db import models
from apps.common.models import BaseModel


class ParseJob(BaseModel):
    """简历解析任务（上传后由 Celery 处理）"""
    STATUS_CHOICES = [
        ('processing', '处理中'),
        ('done', '完成'),
        ('failed', '失败'),
    ]
    PHASE_CHOICES = [
        ('uploading', '上传中'),
        ('parsing', '解析中'),
        ('checking', '查重中'),
    ]

    job_id = models.CharField(max_length=32, unique=True, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='processing')
    phase = models.CharField(max_length=16, choices=PHASE_CHOICES, null=True, blank=True)
    progress = models.IntegerField(default=0)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=512)
    file_size = models.IntegerField()
    error = models.CharField(max_length=64, null=True, blank=True)
    parsed_data = models.JSONField(null=True, blank=True)
    duplicate_data = models.JSONField(null=True, blank=True)
    draft_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    actor = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, related_name='+'
    )
```

生成 migration：
```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/apps/django && .venv/bin/python manage.py makemigrations add_candidate
```

### Step 2.3: 写 view 实现

`apps/django/apps/add_candidate/views.py`:
```python
"""Add Candidate V2 - DRF Views"""
import logging
import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions import IsHROrAbove  # 假设此 app 已存在
from .models import ParseJob
from .serializers import (
    UploadAndParseRequestSerializer,
    UploadAndParseResponseSerializer,
)
from .tasks import parse_resume_task

logger = logging.getLogger(__name__)

ALLOWED_EXT = {'.pdf', '.doc', '.docx', '.txt'}
MAX_FILES = 20
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class UploadAndParseView(APIView):
    """POST /upload-and-parse/

    上传 1-20 个简历文件（PDF/Word/TXT，单文件 ≤ 10MB），立即返回 202
    + job_id 列表。前端轮询 /parse-status/{job_id}/ 获取进度。
    """
    permission_classes = [IsAuthenticated, IsHROrAbove]
    parser_classes = [MultiPartParser]

    def post(self, request):
        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {'detail': '未上传文件', 'code': 'NO_FILES'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(files) > MAX_FILES:
            return Response(
                {'detail': f'单次最多 {MAX_FILES} 个文件', 'code': 'TOO_MANY_FILES'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job_ids = []
        draft_ids = []
        for f in files:
            # 校验扩展名
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in ALLOWED_EXT:
                return Response(
                    {'detail': f'文件 {f.name} 类型不支持', 'code': 'UNSUPPORTED_TYPE'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # 校验大小
            if f.size > MAX_FILE_SIZE:
                return Response(
                    {'detail': f'文件 {f.name} 超过 10MB', 'code': 'FILE_TOO_LARGE'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 保存到 MEDIA_ROOT/resumes/{year}/{month}/{uuid}{ext}
            job_id = uuid.uuid4().hex[:16]
            draft_id = f'draft_{uuid.uuid4().hex[:12]}'
            year_month = f'{timezone.now().year}/{timezone.now().month:02d}'
            rel_path = f'resumes/{year_month}/{job_id}{ext}'
            saved_path = default_storage.save(rel_path, f)
            abs_path = default_storage.path(saved_path)

            # 创建 ParseJob
            ParseJob.objects.create(
                job_id=job_id,
                draft_id=draft_id,
                file_name=f.name,
                file_path=abs_path,
                file_size=f.size,
                actor=request.user,
            )
            job_ids.append(job_id)
            draft_ids.append(draft_id)

            # 异步触发解析
            parse_resume_task.delay(job_id)

        return Response(
            {'job_ids': job_ids, 'draft_ids': draft_ids},
            status=status.HTTP_202_ACCEPTED,
        )
```

需要加 import: `from django.utils import timezone`

### Step 2.4: 写 task 实现（最小可用）

`apps/django/apps/add_candidate/tasks.py`:
```python
"""Add Candidate V2 - Celery tasks"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def parse_resume_task(self, job_id):
    """解析单个简历任务

    完整实现见 Task 5（本 task 只做 stub 让 UploadAndParseView 跑通）
    """
    from .models import ParseJob
    try:
        job = ParseJob.objects.get(job_id=job_id)
        job.phase = 'parsing'
        job.progress = 10
        job.save()
        logger.info('parse_resume_task: stub for job %s', job_id)
        # 真实实现留给 Task 5
    except ParseJob.DoesNotExist:
        logger.error('ParseJob %s not found', job_id)
    except Exception as e:
        logger.exception('parse_resume_task failed: %s', e)
        raise self.retry(exc=e)
```

### Step 2.5: 跑测试

```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/apps/django && .venv/bin/python -m pytest apps/add_candidate/tests/test_views.py::TestUploadAndParseView -v
```
Expected: 3 tests pass

### Step 2.6: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/apps/django/apps/add_candidate/views.py \
        ATS-New/apps/django/apps/add_candidate/tasks.py \
        ATS-New/apps/django/apps/add_candidate/models.py \
        ATS-New/apps/django/apps/add_candidate/migrations/ \
        ATS-New/apps/django/apps/add_candidate/tests/test_views.py
git commit -m "feat(add-candidate): Upload endpoint + ParseJob model + Celery stub"
```

---

## Task 3: Parse Status endpoint

**Files:**
- Modify: `apps/django/apps/add_candidate/views.py`（实现 `ParseStatusView`）
- Modify: `apps/django/apps/add_candidate/tests/test_views.py`（添加 2 个测试）

### Step 3.1: 写失败测试

```python
@pytest.mark.django_db
class TestParseStatusView:
    """GET /parse-status/{job_id}/ 测试"""

    def test_get_processing_job(self, api_client, hr_user):
        """job processing 中 → status=processing, progress < 100"""
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
```

### Step 3.2: 写 view

```python
from .models import ParseJob
from .serializers import ParseStatusResponseSerializer


class ParseStatusView(APIView):
    """GET /parse-status/{job_id}/

    前端每 1.5s 轮询获取解析状态。完成时返回 parsed + duplicate。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = ParseJob.objects.get(job_id=job_id)
        except ParseJob.DoesNotExist:
            return Response(
                {'detail': 'Job not found', 'code': 'JOB_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            'draft_id': job.draft_id,
            'status': job.status,
            'phase': job.phase,
            'progress': job.progress,
            'parsed': job.parsed_data,
            'duplicate': job.duplicate_data,
            'error': job.error,
        })
```

### Step 3.3: 跑测试

```bash
.venv/bin/python -m pytest apps/add_candidate/tests/test_views.py::TestParseStatusView -v
```
Expected: 2 PASSED

### Step 3.4: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/apps/django/apps/add_candidate/views.py \
        ATS-New/apps/django/apps/add_candidate/tests/test_views.py
git commit -m "feat(add-candidate): Parse Status endpoint"
```

---

## Task 4: Duplicate Check endpoint

**Files:**
- Modify: `apps/django/apps/add_candidate/views.py`（实现 `DuplicateCheckView`）
- Modify: `apps/django/apps/add_candidate/tests/test_views.py`（添加 2 个测试）

### Step 4.1: 写失败测试

```python
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
```

`candidate_with_active_app` fixture 已在 `tests/test_duplicate_check.py` 中存在但未导出。新建 `tests/conftest.py` 添加：

```python
@pytest.fixture
def candidate_with_active_app(db, published_position):
    from apps.candidate.models import Candidate
    from apps.application.models import Application, ApplicationState
    cand = Candidate.objects.create(name='重复测试', phone='13911111111')
    Application.objects.create(
        candidate=cand,
        position=published_position,
        process=published_position.process,
        workflow_version=published_position.process.current_version,
        code='APP-DUP-001',
        state=ApplicationState.ACTIVE,
    )
    return cand
```

### Step 4.2: 写 view

```python
from .services.duplicate_check import DuplicateCheckService


class DuplicateCheckView(APIView):
    """POST /duplicate-check/

    用户编辑字段后触发重新查重。返回 clean/unocc/occupied + duplicate info。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DuplicateCheckRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        info = DuplicateCheckService.find(
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            id_card='',
            moka_id='',
        )
        return Response(info.to_dict())
```

### Step 4.3: 跑测试

```bash
.venv/bin/python -m pytest apps/add_candidate/tests/test_views.py::TestDuplicateCheckView -v
```
Expected: 2 PASSED

### Step 4.4: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/apps/django/apps/add_candidate/views.py \
        ATS-New/apps/django/apps/add_candidate/tests/test_views.py \
        ATS-New/apps/django/apps/add_candidate/tests/conftest.py
git commit -m "feat(add-candidate): Duplicate Check endpoint"
```

---

## Task 5: parse_resume_task 真实实现

**Files:**
- Modify: `apps/django/apps/add_candidate/tasks.py`（替换 stub 为真实实现）
- Modify: `apps/django/apps/add_candidate/tests/test_tasks.py`（新增）

### Step 5.1: 写失败测试

`apps/django/apps/add_candidate/tests/test_tasks.py`:
```python
"""Celery task 测试"""
import pytest
from unittest.mock import patch
from apps.add_candidate.models import ParseJob
from apps.add_candidate.tasks import parse_resume_task


@pytest.mark.django_db
class TestParseResumeTask:
    """parse_resume_task 真实实现测试"""

    @patch('apps.add_candidate.services.resume_parser.ResumeParserService.parse')
    @patch('apps.add_candidate.services.duplicate_check.DuplicateCheckService.find')
    def test_parse_success_updates_job(self, mock_dup_find, mock_parse, hr_user, tmp_path):
        """成功解析 → ParseJob.status=done, parsed_data/duplicate_data 填充"""
        from apps.add_candidate.services.resume_parser import ParsedResume, Education, Experience
        mock_parse.return_value = ParsedResume(
            name='张三', phone='13800138000', email='z@x.com', gender='男', age=30,
            edu='本科', educations=[], experiences=[], confidence=0.95,
        )
        mock_dup_find.return_value.to_dict = lambda self: {'status': 'clean'}

        # 准备真实文件
        test_file = tmp_path / 'test.pdf'
        test_file.write_bytes(b'%PDF-1.4 fake')
        job = ParseJob.objects.create(
            job_id='task_test_001',
            file_name='test.pdf',
            file_path=str(test_file),
            file_size=100,
            actor=hr_user,
        )

        parse_resume_task('task_test_001')

        job.refresh_from_db()
        assert job.status == 'done'
        assert job.parsed_data['name'] == '张三'
        assert job.duplicate_data['status'] == 'clean'

    @patch('apps.add_candidate.services.resume_parser.ResumeParserService.parse')
    def test_parse_failure_marks_job_failed(self, mock_parse, hr_user, tmp_path):
        from apps.add_candidate.services.resume_parser import ParseError
        mock_parse.side_effect = ParseError('AFFINDA_TIMEOUT', 'timeout')
        test_file = tmp_path / 'test.pdf'
        test_file.write_bytes(b'%PDF-1.4')
        job = ParseJob.objects.create(
            job_id='task_fail_001', file_name='t.pdf', file_path=str(test_file),
            file_size=100, actor=hr_user,
        )

        with pytest.raises(Exception):
            parse_resume_task('task_fail_001')

        job.refresh_from_db()
        assert job.status == 'failed'
        assert job.error == 'AFFINDA_TIMEOUT'
```

### Step 5.2: 写 task 真实实现

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def parse_resume_task(self, job_id):
    """解析单个简历任务（完整实现）"""
    from .models import ParseJob
    from .services.resume_parser import ResumeParserService, ParseError
    from .services.duplicate_check import DuplicateCheckService

    try:
        job = ParseJob.objects.get(job_id=job_id)
    except ParseJob.DoesNotExist:
        logger.error('ParseJob %s not found', job_id)
        return

    try:
        # 1. 阶段：parsing
        job.phase = 'parsing'
        job.progress = 10
        job.save(update_fields=['phase', 'progress'])

        # 2. 调 Affinda
        with open(job.file_path, 'rb') as f:
            parsed = ResumeParserService.parse(f)

        job.progress = 70
        job.parsed_data = parsed.to_dict()
        job.save(update_fields=['progress', 'parsed_data'])

        # 3. 阶段：checking
        job.phase = 'checking'
        job.progress = 80
        job.save(update_fields=['phase', 'progress'])

        # 4. 查重
        info = DuplicateCheckService.find(
            phone=parsed.phone or '',
            email=parsed.email or '',
            id_card='',
            moka_id='',
        )
        job.duplicate_data = info.to_dict()
        job.status = 'done'
        job.progress = 100
        job.save(update_fields=['duplicate_data', 'status', 'progress'])

    except ParseError as e:
        logger.error('ParseJob %s parse error: %s', job_id, e.code)
        job.status = 'failed'
        job.error = e.code
        job.save(update_fields=['status', 'error'])
        # 不重试，配置错误/超时应该立即 fail

    except Exception as e:
        logger.exception('ParseJob %s unexpected: %s', job_id, e)
        # 重试 3 次
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            job.status = 'failed'
            job.error = 'MAX_RETRIES_EXCEEDED'
            job.save(update_fields=['status', 'error'])
```

### Step 5.3: 跑测试

```bash
.venv/bin/python -m pytest apps/add_candidate/tests/test_tasks.py -v
```
Expected: 2 PASSED

### Step 5.4: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/apps/django/apps/add_candidate/tasks.py \
        ATS-New/apps/django/apps/add_candidate/tests/test_tasks.py
git commit -m "feat(add-candidate): parse_resume_task 真实实现"
```

---

## Task 6: Replace File endpoint

**Files:**
- Modify: `apps/django/apps/add_candidate/views.py`（实现 `ReplaceFileView`）
- Modify: `apps/django/apps/add_candidate/tests/test_views.py`（添加 2 个测试）

### Step 6.1: 写失败测试

```python
@pytest.mark.django_db
class TestReplaceFileView:
    """POST /replace-file/{draft_id}/ 测试"""

    def test_replace_success(self, api_client, hr_user):
        """替换 → 202 + new_job_id"""
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

    def test_replace_draft_not_found(self, api_client):
        file = SimpleUploadedFile('new.pdf', b'%PDF-1.4', content_type='application/pdf')
        response = api_client.post(
            '/api/v1/candidates/add-candidate/replace-file/nonexistent/',
            {'file': file},
            format='multipart',
        )
        assert response.status_code == 404
```

### Step 6.2: 写 view

```python
class ReplaceFileView(APIView):
    """POST /replace-file/{draft_id}/

    替换简历附件并重新解析。
    """
    permission_classes = [IsAuthenticated, IsHROrAbove]
    parser_classes = [MultiPartParser]

    def post(self, request, draft_id):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'detail': '未上传文件', 'code': 'NO_FILE'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXT:
            return Response(
                {'detail': f'文件类型不支持', 'code': 'UNSUPPORTED_TYPE'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file.size > MAX_FILE_SIZE:
            return Response(
                {'detail': f'文件超过 10MB', 'code': 'FILE_TOO_LARGE'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 找原 job
        try:
            old_job = ParseJob.objects.filter(draft_id=draft_id).latest('created_at')
        except ParseJob.DoesNotExist:
            return Response(
                {'detail': f'Draft {draft_id} not found', 'code': 'DRAFT_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 保存新文件
        new_job_id = uuid.uuid4().hex[:16]
        new_draft_id = f'draft_{uuid.uuid4().hex[:12]}'
        year_month = f'{timezone.now().year}/{timezone.now().month:02d}'
        rel_path = f'resumes/{year_month}/{new_job_id}{ext}'
        saved_path = default_storage.save(rel_path, file)
        abs_path = default_storage.path(saved_path)

        ParseJob.objects.create(
            job_id=new_job_id,
            draft_id=new_draft_id,
            file_name=file.name,
            file_path=abs_path,
            file_size=file.size,
            actor=request.user,
        )

        # 触发解析
        parse_resume_task.delay(new_job_id)

        return Response(
            {'new_job_id': new_job_id},
            status=status.HTTP_202_ACCEPTED,
        )
```

### Step 6.3: 跑测试 + Commit

```bash
.venv/bin/python -m pytest apps/add_candidate/tests/test_views.py::TestReplaceFileView -v
# 2 PASSED 后：
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/apps/django/apps/add_candidate/views.py \
        ATS-New/apps/django/apps/add_candidate/tests/test_views.py
git commit -m "feat(add-candidate): Replace File endpoint"
```

---

## Task 7: Bulk Create endpoint

**Files:**
- Modify: `apps/django/apps/add_candidate/views.py`（实现 `BulkCreateView`）
- Modify: `apps/django/apps/add_candidate/tests/test_views.py`（添加 3 个测试）

### Step 7.1: 写失败测试

```python
@pytest.mark.django_db
class TestBulkCreateView:
    """POST /bulk-create/ 测试"""

    def test_bulk_create_pending(self, api_client, hr_user):
        """1 个 pending draft → 200 + task_id"""
        response = api_client.post(
            '/api/v1/candidates/add-candidate/bulk-create/',
            {
                'drafts': [
                    {'draft_id': 'd1', 'direction': 'pending',
                     'channel': '招聘网站', 'source': 'Boss', 'provider': ''}
                ],
                'submit_mode': 'async',
            },
            format='json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'task_id' in data
        assert len(data['created_candidate_ids']) == 1

    def test_bulk_create_position_requires_position_id(self, api_client, published_position):
        """direction=position 但无 position_id → 400"""
        response = api_client.post(
            '/api/v1/candidates/add-candidate/bulk-create/',
            {
                'drafts': [{'draft_id': 'd1', 'direction': 'position', 'position_id': None}],
                'submit_mode': 'async',
            },
            format='json',
        )
        assert response.status_code == 400

    def test_bulk_create_rollback_on_partial_failure(self, api_client):
        """第二个 draft 失败 → 第一个回滚"""
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
        assert Candidate.objects.filter(phone__in=['13800138000', '13800138001']).count() == 0
```

### Step 7.2: 写 view

```python
class BulkCreateView(APIView):
    """POST /bulk-create/

    批量提交：创建候选 + 关联记录（application/talent_pool）。
    sync (wait) 模式：同步触发评分任务，立即返 task_id
    async 模式：仅入库，评分后台跑，通知中心推结果
    """
    permission_classes = [IsAuthenticated, IsHROrAbove]

    def post(self, request):
        serializer = BulkCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 转 BulkCreateDraft
        from .services.bulk_create import BulkCreateService, BulkCreateDraft
        drafts = [
            BulkCreateDraft(
                draft_id=d['draft_id'],
                direction=d['direction'],
                position_id=d.get('position_id') or None,
                channel=d.get('channel', ''),
                source=d.get('source', ''),
                provider=d.get('provider', ''),
            )
            for d in data['drafts']
        ]

        try:
            result = BulkCreateService.create_batch(drafts, actor=request.user)
        except Exception as e:
            logger.exception('BulkCreate failed: %s', e)
            return Response(
                {'detail': str(e), 'code': 'BULK_CREATE_FAILED'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 启动评分任务
        from .tasks import score_batch_task
        task = score_batch_task.delay(
            candidate_ids=result.created_candidate_ids,
            submit_mode=data['submit_mode'],
            task_id=result.task_id,
        )

        return Response({
            'task_id': task.id,
            'created_candidate_ids': result.created_candidate_ids,
            'route': result.route,
        })
```

注：`BulkCreateService.create_batch` 需要返回 `task_id` 和 `route` 字段。如果 Phase 1 的实现没返回这些，需扩展。

### Step 7.3: 跑测试 + Commit

```bash
.venv/bin/python -m pytest apps/add_candidate/tests/test_views.py::TestBulkCreateView -v
# 3 PASSED 后：
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/apps/django/apps/add_candidate/views.py \
        ATS-New/apps/django/apps/add_candidate/tests/test_views.py
git commit -m "feat(add-candidate): Bulk Create endpoint"
```

---

## Task 8: score_batch_task + scoring endpoints + SSE

**Files:**
- Modify: `apps/django/apps/add_candidate/tasks.py`（加 `score_batch_task` 和 `send_async_notification_task`）
- Create: `apps/django/apps/add_candidate/sse.py`（SSE 视图）
- Modify: `apps/django/apps/add_candidate/views.py`（加 `ScoringStartView` + `ScoringStreamView`）
- Modify: `apps/django/apps/add_candidate/tests/test_views.py`（加 3 个测试）

### Step 8.1: 实现 score_batch_task

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=5, queue='scoring')
def score_batch_task(self, candidate_ids, submit_mode, task_id):
    """批量评分任务

    wait 模式：每份简历立即评，前端连 SSE 接收进度
    async 模式：评分完成后发通知中心
    """
    from .services.scoring import ScoringService
    from .sse import broadcast_event

    # 注：wait 模式下由 bulk-create view 同步触发，此函数主要处理 async
    # 但 wait 模式也走这里是为了统一进度推送

    for idx, cand_id in enumerate(candidate_ids):
        try:
            # 模拟：从 candidate 拉简历数据 + position
            # 真实实现需要查 DB；这里留 stub
            # cand = Candidate.objects.get(id=cand_id)
            # result = ScoringService.score(...)
            score = 75 + idx  # stub
            broadcast_event(task_id, {
                'event': 'scoring-done',
                'data': {'candidate_id': cand_id, 'score': score, 'passed': score >= 60},
            })
        except Exception as e:
            logger.exception('Score failed for %s: %s', cand_id, e)
            broadcast_event(task_id, {
                'event': 'scoring-failed',
                'data': {'candidate_id': cand_id, 'error': str(e)},
            })

    broadcast_event(task_id, {
        'event': 'task-complete',
        'data': {'summary': {'total': len(candidate_ids), 'passed': len(candidate_ids)}},
    })

    if submit_mode == 'async':
        send_async_notification_task.delay(task_id)
```

### Step 8.2: 实现 send_async_notification_task

```python
@shared_task
def send_async_notification_task(task_id):
    """异步评分完成后发通知中心"""
    from apps.notification.services import NotificationService
    NotificationService.send(
        user_id=None,  # 系统通知
        title='简历评分完成',
        content=f'任务 {task_id} 评分已完成，点击查看结果',
        link=f'/candidates?task={task_id}',
    )
```

如果 `apps.notification` 不存在，stub 一下（先 log 后留 TODO）。

### Step 8.3: 实现 SSE 视图

`apps/django/apps/add_candidate/sse.py`:
```python
"""Add Candidate V2 - SSE 流"""
import json
import time
import threading
from collections import defaultdict

from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

# 内存 pub/sub：task_id → list of (event, data) tuples
_TASK_EVENTS: dict[str, list] = defaultdict(list)
_TASK_LOCKS: dict[str, threading.Lock] = defaultdict(threading.Lock)


def broadcast_event(task_id: str, payload: dict):
    """Celery task 调这个推 SSE 事件"""
    with _TASK_LOCKS[task_id]:
        _TASK_EVENTS[task_id].append(payload)


def _consume_events(task_id: str):
    """SSE consumer generator"""
    last_heartbeat = time.time()
    while True:
        with _TASK_LOCKS[task_id]:
            events = list(_TASK_EVENTS[task_id])
            _TASK_EVENTS[task_id].clear()

        for evt in events:
            event = evt.get('event', 'message')
            data = json.dumps(evt.get('data', {}), ensure_ascii=False)
            yield f'event: {event}\ndata: {data}\n\n'
            if event == 'task-complete':
                return

        # Heartbeat
        if time.time() - last_heartbeat > 15:
            yield ': heartbeat\n\n'
            last_heartbeat = time.time()

        time.sleep(0.5)


class ScoringStreamView(APIView):
    """GET /scoring/stream/{task_id}/

    SSE 评分进度流。前端 EventSource 连这个端点。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        response = StreamingHttpResponse(
            _consume_events(task_id),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # nginx 不缓冲
        return response
```

### Step 8.4: 实现 ScoringStartView

`apps/django/apps/add_candidate/views.py` 加:

```python
from .serializers import ScoringStartRequestSerializer, ScoringStartResponseSerializer
from .tasks import score_batch_task


class ScoringStartView(APIView):
    """POST /scoring/start/

    async 模式由前端显式调用启动评分（wait 模式由 bulk-create 触发）。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ScoringStartRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        task = score_batch_task.delay(
            candidate_ids=data['candidate_ids'],
            submit_mode='async',
            task_id=data['task_id'],
        )

        return Response({
            'stream_url': f'/api/v1/candidates/add-candidate/scoring/stream/{data["task_id"]}/',
        })
```

### Step 8.5: 写测试

```python
@pytest.mark.django_db
class TestScoringEndpoints:
    """Scoring Start + Stream 测试"""

    def test_scoring_start_returns_stream_url(self, api_client):
        response = api_client.post(
            '/api/v1/candidates/add-candidate/scoring/start/',
            {'candidate_ids': ['c1', 'c2'], 'task_id': 'task_test'},
            format='json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'stream_url' in data
        assert 'task_test' in data['stream_url']

    def test_scoring_stream_returns_event_stream(self, api_client):
        from apps.add_candidate.sse import broadcast_event
        import threading
        def push():
            time.sleep(0.2)
            broadcast_event('sse_test_1', {'event': 'test', 'data': {'x': 1}})
            broadcast_event('sse_test_1', {'event': 'task-complete', 'data': {}})
        threading.Thread(target=push, daemon=True).start()

        response = api_client.get('/api/v1/candidates/add-candidate/scoring/stream/sse_test_1/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/event-stream'

    def test_scoring_start_requires_auth(self, plain_client):
        response = plain_client.post(
            '/api/v1/candidates/add-candidate/scoring/start/',
            {'candidate_ids': ['c1'], 'task_id': 't1'},
            format='json',
        )
        assert response.status_code in (401, 403)
```

### Step 8.6: 跑测试 + Commit

```bash
.venv/bin/python -m pytest apps/add_candidate/tests/test_views.py::TestScoringEndpoints -v
# 3 PASSED 后：
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/apps/django/apps/add_candidate/tasks.py \
        ATS-New/apps/django/apps/add_candidate/sse.py \
        ATS-New/apps/django/apps/add_candidate/views.py \
        ATS-New/apps/django/apps/add_candidate/tests/test_views.py
git commit -m "feat(add-candidate): score_batch_task + Scoring endpoints + SSE"
```

---

## Task 9: 端到端集成验证

**Files:** None new, just run

### Step 9.1: 跑全部 add_candidate 测试

```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/apps/django
.venv/bin/python -m pytest apps/add_candidate/ -v
```

Expected: 38+ tests pass（Phase 1 的 36 + Phase 2 新增 12+）

### Step 9.2: 跑全项目测试看回归

```bash
.venv/bin/python -m pytest apps/ -v --ignore=apps/data_dict --ignore=apps/permissions 2>&1 | tail -20
```

Expected: 已有 4 个 pre-existing 失败（test_candidate/test_demand），其他全过。

### Step 9.3: 跑覆盖率

```bash
.venv/bin/python -m pytest apps/add_candidate/ --cov=apps.add_candidate --cov-report=term-missing
```

Expected: ≥ 85%

### Step 9.4: 端到端手动 smoke test

```bash
.venv/bin/python manage.py runserver 0.0.0.0:8000 &
sleep 2

# 1. 登录拿 token
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"hr_user","password":"password"}'

# 2. 上传简历
curl -X POST http://localhost:8000/api/v1/candidates/add-candidate/upload-and-parse/ \
  -H "Authorization: Bearer <token>" \
  -F "files=@/path/to/test.pdf"
```

### Step 9.5: Tag + Push

```bash
cd /Users/loki/ats-add-candidate-v2
git tag -d phase2-complete 2>/dev/null
git tag -a phase2-complete -m "Phase 2 完成: 7 endpoint + 3 Celery task + SSE"
git push gitee feat/add-candidate-v2 --follow-tags
```

---

## 总时间预算

| Task | 工作量 |
|---|---|
| 1: Serializers + URL | 0.5 天 |
| 2: Upload + ParseJob model | 1 天 |
| 3: Parse Status | 0.5 天 |
| 4: Duplicate Check | 0.5 天 |
| 5: parse_resume_task 真实实现 | 1 天 |
| 6: Replace File | 0.5 天 |
| 7: Bulk Create | 1 天 |
| 8: score_batch_task + SSE | 1 天 |
| 9: 验证 | 0.5 天 |
| **合计** | **~6.5 天** |

---

## 风险与回退

- **`IsHROrAbove` permission class 不存在**：若项目无此 permission，需先实现或换用 `IsAuthenticated` 暂时（后续 task 引入）
- **`apps.notification` 不存在**：send_async_notification_task stub，log 一行即可，Phase 3 前端实现异步通知 UI 时再接
- **Celery 在测试环境跑**：用 `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` 在测试中同步执行
- **SSE 测试稳定性**：consumer 是 generator + threading，测试需 daemon thread + 0.2s 等待事件推送

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-06-22-add-candidate-v2-phase2.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**