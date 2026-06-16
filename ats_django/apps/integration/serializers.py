"""Integration Serializers (PRD v4 §14.4)"""
from rest_framework import serializers

from .models import IntegrationConfig, IntegrationSyncLog


class IntegrationConfigSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = IntegrationConfig
        fields = [
            'id', 'type', 'type_display', 'name',
            'config', 'field_mapping',
            'is_active', 'last_sync_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_sync_at', 'created_at', 'updated_at']


class IntegrationSyncLogSerializer(serializers.ModelSerializer):
    config_name = serializers.CharField(source='config.name', read_only=True, default='')

    class Meta:
        model = IntegrationSyncLog
        fields = [
            'id', 'config', 'config_name',
            'sync_type', 'status',
            'total_count', 'success_count', 'failed_count',
            'error_message', 'created_at',
        ]
        read_only_fields = fields  # 仅由 services 写入
