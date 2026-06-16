"""GDPR Serializers (PRD v4 §4.4)"""
from rest_framework import serializers

from .models import GDPRRequest


class GDPRRequestSerializer(serializers.ModelSerializer):
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
            'submitted_email', 'verification_code',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'processed_by', 'processed_at',
            'result', 'created_at', 'updated_at',
        ]


class GDPRRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GDPRRequest
        fields = [
            'candidate', 'request_type',
            'submitted_email', 'verification_code',
        ]


class GDPRProcessSerializer(serializers.Serializer):
    """GDPR 处理请求"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    result = serializers.CharField(required=False, allow_blank=True)
    reject_reason = serializers.CharField(required=False, allow_blank=True)
