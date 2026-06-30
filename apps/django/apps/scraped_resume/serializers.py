"""scraped_resume serializers — 2026-06-29 stub."""
from rest_framework import serializers


class ScrapedResumeSerializer(serializers.Serializer):
    """空 stub serializer - 真实字段留给 G30."""
    id = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True, default='PENDING')
