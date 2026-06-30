"""external_sync serializers — 2026-06-29 stub."""
from rest_framework import serializers


class CompanySyncSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    companyId = serializers.CharField(source='company_id', read_only=True)
    externalSystem = serializers.CharField(source='external_system', read_only=True)
    syncStatus = serializers.CharField(source='sync_status', read_only=True, default='PENDING')
    lastSyncAt = serializers.DateTimeField(source='last_sync_at', read_only=True, allow_null=True)
    retryCount = serializers.IntegerField(source='retry_count', read_only=True, default=0)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
