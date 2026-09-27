"""Add Candidate V2 - DRF Serializers

PRD v2 §5.2 endpoint request/response shapes.

7 个 endpoint 对应 9 个 serializer：
- UploadAndParseRequest / Response
- ParseStatusResponse
- DuplicateCheckRequest / (response 用 dict，无独立 serializer)
- ReplaceFileResponse
- BulkCreateDraft / BulkCreateRequest / BulkCreateResponse
- ScoringStartRequest / ScoringStartResponse
"""
from __future__ import annotations

from rest_framework import serializers


# ============================================================
# Upload & Parse
# ============================================================
class UploadAndParseRequest(serializers.Serializer):
    """POST /candidates/upload-and-parse/ — multipart request.

    文件字段由视图层通过 request.FILES 处理（不在 serializer 字段里）。
    """

    pass  # multipart: files in request.FILES, no body fields in v1


class UploadAndParseResponse(serializers.Serializer):
    """Response 202: { job_ids: [...], draft_ids: [...] }"""

    job_ids = serializers.ListField(child=serializers.CharField())
    draft_ids = serializers.ListField(child=serializers.CharField())


class ParseStatusResponse(serializers.Serializer):
    """GET /candidates/parse-status/{job_id}/ — 轮询响应。

    status: processing | done | failed
    phase: uploading | parsing | checking | null
    """

    draft_id = serializers.CharField()
    status = serializers.CharField()
    phase = serializers.CharField(allow_null=True, required=False)
    progress = serializers.IntegerField(min_value=0, max_value=100)
    parsed = serializers.DictField(required=False, default=dict)
    duplicate = serializers.DictField(required=False, default=dict)
    error = serializers.CharField(allow_null=True, required=False)


# ============================================================
# Duplicate Check
# ============================================================
class DuplicateCheckRequest(serializers.Serializer):
    """POST /candidates/duplicate-check/ — 重查重（用户改字段后触发）。"""

    draft_id = serializers.CharField()
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)


# ============================================================
# Replace File
# ============================================================
class ReplaceFileResponse(serializers.Serializer):
    """Response 202: { new_job_id }"""

    new_job_id = serializers.CharField()


# ============================================================
# Bulk Create
# ============================================================
class BulkCreateDraftSerializer(serializers.Serializer):
    """单个 draft 的提交参数。"""

    draft_id = serializers.CharField()
    direction = serializers.ChoiceField(choices=['pending', 'talent', 'position'])
    # 人才库(pending/talent)方向无关联职位，前端会传 position_id=null。
    # 业务逻辑(_validate)仅 position 方向强制要求 position_id，故此处必须同时 allow_null。
    position_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    channel = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class BulkCreateRequest(serializers.Serializer):
    """POST /candidates/bulk-create/ — Step 2 提交。"""

    drafts = BulkCreateDraftSerializer(many=True)
    submit_mode = serializers.ChoiceField(choices=['wait', 'async'])


class BulkCreateResponse(serializers.Serializer):
    """Response 200/202: { task_id, created_candidate_ids, route }"""

    task_id = serializers.CharField()
    created_candidate_ids = serializers.ListField(child=serializers.CharField())
    route = serializers.DictField(child=serializers.CharField())


# ============================================================
# Scoring
# ============================================================
class ScoringStartRequest(serializers.Serializer):
    """POST /candidates/scoring/start/ — async 模式显式调用。"""

    candidate_ids = serializers.ListField(child=serializers.CharField())
    task_id = serializers.CharField()


class ScoringStartResponse(serializers.Serializer):
    """Response 202: { stream_url }"""

    stream_url = serializers.CharField()
