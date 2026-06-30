"""duplicate_check serializers — 2026-06-29 stub."""
from rest_framework import serializers


class DuplicateCandidateSerializer(serializers.Serializer):
    candidate = serializers.DictField()
    score = serializers.FloatField()
    matchType = serializers.CharField(source='match_type')
