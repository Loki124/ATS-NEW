"""Notification Serializers (PRD v4 §14.10)"""
from rest_framework import serializers

from .models import NotificationLog, NotificationTemplate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'code', 'name', 'event',
            'templates', 'variables', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient.username', read_only=True, default='')
    template_name = serializers.CharField(source='template.name', read_only=True, default='')
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            'id', 'template', 'template_name',
            'recipient', 'recipient_name',
            'channel', 'channel_display',
            'subject', 'content',
            'event', 'context',
            'sent_at', 'read_at', 'failed_reason',
            'created_at',
        ]


class NotificationLogListSerializer(NotificationLogSerializer):
    class Meta(NotificationLogSerializer.Meta):
        fields = NotificationLogSerializer.Meta.fields


class NotificationMarkReadSerializer(serializers.Serializer):
    """标记已读请求"""
    notification_ids = serializers.ListField(child=serializers.CharField(), required=False)
    mark_all = serializers.BooleanField(default=False)
