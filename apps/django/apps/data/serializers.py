"""data serializers — 2026-06-29 stub."""
from rest_framework import serializers


class DataSubscriptionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    userId = serializers.CharField(source='user_id')
    userName = serializers.CharField(source='user_name')
    resource = serializers.CharField()
    metric = serializers.CharField()
    channel = serializers.CharField()
    schedule = serializers.CharField()
    isActive = serializers.BooleanField(source='is_active')
    runCount = serializers.IntegerField(source='run_count')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
