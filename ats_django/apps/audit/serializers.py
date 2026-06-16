"""Audit Serializers (PRD v4 §4.4, §13)"""
from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True, default='')

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_name',
            'action', 'action_display',
            'entity', 'entity_id', 'field',
            'old_value', 'new_value',
            'ip', 'user_agent', 'request_id',
            'created_at',
        ]
        read_only_fields = fields  # 只读 - 由 middleware/signals 写入
