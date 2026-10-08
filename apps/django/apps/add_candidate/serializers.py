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


class ManualCreateRequest(serializers.Serializer):
    """POST /candidates/add-candidate/manual-create/ — 无文件手动建草稿。

    前端「手动填写」模式提交姓名/手机/邮箱等基础信息，后端直接落一条
    status='done' 的 ParseJob（parsed_data=手动数据，无附件），并即时查重，
    复用整条 V2 管线（Step1 编辑 / Step2 去向 / bulk-create）。
    """

    name = serializers.CharField(required=True, allow_blank=False)
    phone = serializers.CharField(required=True, allow_blank=False)
    email = serializers.EmailField(required=True, allow_blank=False)
    gender = serializers.CharField(required=False, allow_blank=True)
    age = serializers.IntegerField(required=False, allow_null=True)
    file_name = serializers.CharField(required=False, allow_blank=True)


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
    # 2026-10-08: 手动填写/编辑覆盖。前端发送 merged = {...parsed, ...edited} 的姓名手机邮箱
    # 与完整 parsed_data，后端优先采用（修复「手动字段被自动清理」——此前 submit 从不发 edited）。
    # 旧前端不传这些字段 → validated_data 不含 → 回落 job.parsed_data（向后兼容）。
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    parsed_data = serializers.DictField(required=False, allow_null=True)


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
