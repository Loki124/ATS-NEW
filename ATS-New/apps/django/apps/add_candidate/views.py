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

from rest_framework.views import APIView


class UploadAndParseView(APIView):
    """POST /candidates/upload-and-parse/

    上传文件 + 触发商业简历解析 API（Affinda）。
    Phase 2 Task 2 填充 ResumeParserService 调用 + Celery 任务。
    """

    pass


class ParseStatusView(APIView):
    """GET /candidates/parse-status/<job_id>/

    前端每 1.5s 轮询解析状态。
    Phase 2 Task 3 填充 Redis 状态读取。
    """

    pass


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
