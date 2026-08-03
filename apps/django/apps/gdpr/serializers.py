"""GDPR Serializers (PRD v4 §4.4)"""
from rest_framework import serializers

from .models import (
    GDPRRequest,
    VERIFICATION_CODE_LENGTH,
    VERIFICATION_CODE_TTL_MINUTES,
)


class GDPRRequestSerializer(serializers.ModelSerializer):
    """GDPR 请求详情 (2026-08-03 S2: 移除 verification_code 字段, 加 attempts/expires_at/verified_at)"""
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    candidate_name = serializers.CharField(source='candidate.name', read_only=True, default='')
    processed_by_name = serializers.CharField(source='processed_by.username', read_only=True, default='')

    class Meta:
        model = GDPRRequest
        fields = [
            'id', 'candidate', 'candidate_name',
            'request_type', 'request_type_display',
            'status', 'status_display',
            'processed_by', 'processed_by_name',
            'processed_at', 'result', 'reject_reason',
            'submitted_email',
            # 2026-08-03: 验证码相关 (注意: hash/expires_at/attempts 内部字段, 不暴露 hash)
            'verification_code_expires_at',
            'verification_code_attempts',
            'verified_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'processed_by', 'processed_at',
            'result', 'created_at', 'updated_at',
            'verification_code_expires_at', 'verification_code_attempts',
            'verified_at',
        ]


class GDPRRequestCreateSerializer(serializers.ModelSerializer):
    """GDPR 请求创建 (候选人提交, 不传验证码 — 由 system 自动生成 + 通过 email 通知)

    2026-08-03 S2: 验证流程是
      1) 候选人 POST /api/v1/gdpr/requests/ 提交 (不带验证码)
      2) system 生成 8 位 hex code, hash 存, 通过邮件/SMS 发给候选人
      3) 候选人 POST /api/v1/gdpr/requests/{id}/verify/ 提交 code
      4) 超管看到 status=PENDING 才能 process (ApproveAndForget/ApproveAndExport)
    """
    class Meta:
        model = GDPRRequest
        fields = ['candidate', 'request_type', 'submitted_email']


class GDPRVerifySerializer(serializers.Serializer):
    """候选人验证验证码"""
    verification_code = serializers.CharField(
        max_length=VERIFICATION_CODE_LENGTH * 2,  # hex 可能被 base32/64 编码, 给 2x 长度缓冲
        min_length=VERIFICATION_CODE_LENGTH,
        help_text=f'{VERIFICATION_CODE_LENGTH} 位 hex 验证码 (15 分钟内有效)',
    )


class GDPRProcessSerializer(serializers.Serializer):
    """GDPR 处理请求 (超管)"""
    action = serializers.ChoiceField(choices=['approve_forget', 'approve_export', 'reject'])
    result = serializers.CharField(required=False, allow_blank=True)
    reject_reason = serializers.CharField(required=False, allow_blank=True)
