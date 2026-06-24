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
from .services.duplicate_check import DuplicateCheckService
from .tasks import parse_resume_task, score_batch_task

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

    用户编辑字段后触发重新查重。返回 clean/unocc/occupied + duplicate info。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .serializers import DuplicateCheckRequest
        serializer = DuplicateCheckRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        info = DuplicateCheckService.find(
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            id_card='',
            moka_id='',
        )
        return Response(info.to_dict())


class ReplaceFileView(APIView):
    """POST /candidates/replace-file/<draft_id>/

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

        # 找原 job（按 draft_id 找最近一个）
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


class BulkCreateView(APIView):
    """POST /candidates/bulk-create/

    批量提交：创建候选 + 关联记录（application/talent_pool）。
    sync (wait) 模式：同步触发评分任务，立即返 task_id
    async 模式：仅入库，评分后台跑，通知中心推结果
    """
    permission_classes = [IsAuthenticated, IsHROrAbove]

    def post(self, request):
        from .serializers import BulkCreateRequest
        from .services.bulk_create import BulkCreateService, BulkCreateDraft, BulkCreateError

        serializer = BulkCreateRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 收集 draft_id → ParseJob 映射（用于补充 name/phone/email/parsed_data）
        draft_ids = [d['draft_id'] for d in data['drafts']]
        jobs = {j.draft_id: j for j in ParseJob.objects.filter(draft_id__in=draft_ids)}

        # 转 BulkCreateDraft
        drafts = []
        for d in data['drafts']:
            job = jobs.get(d['draft_id'])
            parsed = (job.parsed_data or {}) if job else {}
            drafts.append(
                BulkCreateDraft(
                    draft_id=d['draft_id'],
                    direction=d['direction'],
                    name=parsed.get('name') or '',
                    phone=parsed.get('phone') or '',
                    email=parsed.get('email') or '',
                    parsed_data=parsed,
                    position_id=d.get('position_id') or None,
                    channel=d.get('channel', '招聘网站'),
                    source=d.get('source', ''),
                    provider=d.get('provider', ''),
                )
            )

        try:
            result = BulkCreateService.create_batch(drafts, actor=request.user)
        except BulkCreateError as e:
            logger.warning('BulkCreate failed: %s', e)
            return Response(
                {'detail': str(e), 'code': e.code, 'draft_id': e.draft_id},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception('BulkCreate unexpected error: %s', e)
            return Response(
                {'detail': str(e), 'code': 'BULK_CREATE_FAILED'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 启动评分任务（Task 8 实现，Task 7 暂用 stub）
        try:
            task = score_batch_task.delay(
                candidate_ids=result.created_candidate_ids,
                submit_mode=data['submit_mode'],
                task_id=f'batch_{uuid.uuid4().hex[:12]}',
            )
            task_id = task.id
        except Exception as e:
            # Redis/Celery 不可用时降级 — task_id 用本地 uuid 占位
            logger.warning('Celery unavailable, falling back to local task_id: %s', e)
            task_id = f'local_{uuid.uuid4().hex[:12]}'

        return Response({
            'task_id': task_id,
            'created_candidate_ids': result.created_candidate_ids,
            'route': result.route,
        })


class ScoringStartView(APIView):
    """POST /candidates/scoring/start/

    async 模式由前端显式调用启动评分（wait 模式由 bulk-create 触发）。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .serializers import ScoringStartRequest
        from .tasks import score_batch_task

        serializer = ScoringStartRequest(data=request.data)
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


class ScoringStreamView(APIView):
    """GET /candidates/scoring/stream/<task_id>/  (SSE)

    同步评分进度流。真实实现在 sse 模块 — 这里 re-export 保持向后兼容。
    """
    pass
