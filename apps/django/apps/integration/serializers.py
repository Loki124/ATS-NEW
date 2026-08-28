"""Integration Serializers (PRD v4 §14.4)"""
import json

from rest_framework import serializers

from .crypto import SENSITIVE_KEYS, encrypt_secret_dict
from .models import (
    IntegrationConfig,
    IntegrationSyncLog,
    BackgroundCheckOrder,
    BackgroundCheckOrderEvent,
)


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
    # 2026-08-28 寇豆码: 全局审计视图需要供应商 provider；config 已 select_related
    config_provider = serializers.CharField(source='config.provider', read_only=True, default='')

    class Meta:
        model = IntegrationSyncLog
        fields = [
            'id', 'config', 'config_name', 'config_provider',
            'sync_type', 'status',
            'total_count', 'success_count', 'failed_count',
            'endpoint', 'method', 'direction', 'duration_ms',
            'error_message', 'created_at',
        ]
        read_only_fields = fields  # 仅由 services 写入


class BackgroundCheckOrderEventSerializer(serializers.ModelSerializer):
    """订单状态机转移事件（只读，由 services 写入）"""
    order_number = serializers.CharField(source='order.order_number', read_only=True, default='')
    from_status_display = serializers.SerializerMethodField()
    to_status_display = serializers.SerializerMethodField()

    class Meta:
        model = BackgroundCheckOrderEvent
        fields = [
            'id', 'order', 'order_number', 'from_status', 'to_status',
            'from_status_display', 'to_status_display',
            'risk_level', 'report_url', 'completion_time',
            'source', 'is_legal_transition', 'raw_payload', 'created_at',
        ]
        read_only_fields = fields

    def get_from_status_display(self, obj):
        from .models import BGOrderStatus
        return BGOrderStatus.label_of(obj.from_status)

    def get_to_status_display(self, obj):
        from .models import BGOrderStatus
        return BGOrderStatus.label_of(obj.to_status)


class BackgroundCheckOrderSerializer(serializers.ModelSerializer):
    """背调订单（状态机主体，列表/详情通用）"""
    config_name = serializers.CharField(source='config.name', read_only=True, default='')
    config_provider = serializers.CharField(source='config.provider', read_only=True, default='')
    status_display = serializers.SerializerMethodField()
    risk_level_display = serializers.SerializerMethodField()

    class Meta:
        model = BackgroundCheckOrder
        fields = [
            'id', 'config', 'config_name', 'config_provider',
            'order_number', 'candidate_id', 'candidate_name',
            'status', 'status_display', 'status_name',
            'risk_level', 'risk_level_display', 'report_url', 'completion_time',
            'latest_payload', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_status_display(self, obj):
        from .models import BGOrderStatus
        return obj.status_label

    def get_risk_level_display(self, obj):
        from .models import BGRiskLevel
        return obj.risk_label


class BackgroundCheckOrderDetailSerializer(BackgroundCheckOrderSerializer):
    """订单详情：附加状态机转移历史"""
    events = BackgroundCheckOrderEventSerializer(many=True, read_only=True)

    class Meta(BackgroundCheckOrderSerializer.Meta):
        fields = BackgroundCheckOrderSerializer.Meta.fields + ['events']
