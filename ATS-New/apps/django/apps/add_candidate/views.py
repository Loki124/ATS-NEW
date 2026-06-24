"""Add Candidate V2 - DRF APIViews

7 个 endpoint（Phase 2 Task 1 仅为占位，Task 2+ 填充业务逻辑）：

| Endpoint                                     | Method | View Class               |
|----------------------------------------------|--------|--------------------------|
| /api/v1/candidates/upload-and-parse/         | POST   | UploadAndParseView       |
| /api/v1/candidates/parse-status/<job_id>/    | GET    | ParseStatusView          |
| /api/v1/candidates/duplicate-check/          | POST   | DuplicateCheckView       |
| /api/v1/candidates/replace-file/<draft_id>/  | POST   | ReplaceFileView          |
| /api/v1/candidates/bulk-create/              | POST   | BulkCreateView           |
| /api/v1/candidates/scoring/start/            | POST   | ScoringStartView         |
| /api/v1/candidates/scoring/stream/<task_id>/ | GET    | ScoringStreamView (SSE)  |

Phase 1 Task 1.4：先创建占位 APIView（最小 class XxxView(APIView): pass）
确保 URL resolve 通过即可。Task 2 起逐步替换为真实实现。
"""
from __future__ import annotations

import logging
import os
import uuid

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsHROrAbove

from .models import ParseJob
from .tasks import parse_resume_task

logger = logging.getLogger(__name__)

ALLOWED_EXT = {'.pdf', '.doc', '.docx', '.txt'}
MAX_FILES = 20
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class UploadAndParseView(APIView):
    """POST /candidates/upload-and-parse/

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
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in ALLOWED_EXT:
                return Response(
                    {'detail': f'文件 {f.name} 类型不支持', 'code': 'UNSUPPORTED_TYPE'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if f.size > MAX_FILE_SIZE:
                return Response(
                    {'detail': f'文件 {f.name} 超过 10MB', 'code': 'FILE_TOO_LARGE'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job_id = uuid.uuid4().hex[:16]
            draft_id = f'draft_{uuid.uuid4().hex[:12]}'
            year_month = f'{timezone.now().year}/{timezone.now().month:02d}'
            rel_path = f'resumes/{year_month}/{job_id}{ext}'
            saved_path = default_storage.save(rel_path, f)
            abs_path = default_storage.path(saved_path)

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

            parse_resume_task.delay(job_id)

        return Response(
            {'job_ids': job_ids, 'draft_ids': draft_ids},
            status=status.HTTP_202_ACCEPTED,
        )


class ParseStatusView(APIView):
    """GET /candidates/parse-status/<job_id>/

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


class DuplicateCheckView(APIView):
    """POST /candidates/duplicate-check/

    重查重（用户改字段后触发，debounce 800ms）。
    Phase 2 Task 3 填充 DuplicateCheckService 调用。
    """

    pass


class ReplaceFileView(APIView):
    """POST /candidates/replace-file/<draft_id>/

    替换附件并重新解析。
    Phase 2 Task 2 填充 ResumeParserService 重跑。
    """

    pass


class BulkCreateView(APIView):
    """POST /candidates/bulk-create/

    批量提交（创建候选 + application + talent pool）+ 同步/异步评分路由。
    Phase 2 Task 4 填充 BulkCreateService + 3 方向路由 + 幂等性。
    """

    pass


class ScoringStartView(APIView):
    """POST /candidates/scoring/start/

    async 模式显式触发评分任务。
    Phase 2 Task 5 填充 Celery task 派发。
    """

    pass


class ScoringStreamView(APIView):
    """GET /candidates/scoring/stream/<task_id>/  (SSE)

    同步评分进度流。
    Phase 2 Task 5 填充 StreamingHttpResponse + SSE 事件。
    """

    pass
