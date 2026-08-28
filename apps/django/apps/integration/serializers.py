"""Integration Serializers (PRD v4 §14.4)"""
import json

from rest_framework import serializers

from .crypto import SENSITIVE_KEYS, encrypt_secret_dict
from .models import IntegrationConfig, IntegrationSyncLog


class IntegrationConfigSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    secret = serializers.JSONField(
        write_only=True, required=False, default=dict,
        help_text='明文敏感凭据，如 {"api_key": "..."}；后端按类型加密存入 encrypted_secret',
    )

    class Meta:
        model = IntegrationConfig
        fields = [
            'id', 'type', 'type_display', 'name', 'provider',
            'config', 'field_mapping', 'secret',
            'is_active', 'last_sync_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_sync_at', 'created_at', 'updated_at']

    def _save_secret(self, instance, secret):
        if not secret:
            return
        encrypted = encrypt_secret_dict(secret or {}, SENSITIVE_KEYS.get(instance.type, []))
        instance.encrypted_secret = json.dumps(encrypted, ensure_ascii=False)
        instance.save(update_fields=['encrypted_secret'])

    def create(self, validated_data):
        secret = validated_data.pop('secret', None)
        instance = super().create(validated_data)
        self._save_secret(instance, secret)
        return instance

    def update(self, instance, validated_data):
        secret = validated_data.pop('secret', None)
        instance = super().update(instance, validated_data)
        self._save_secret(instance, secret)
        return instance


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
