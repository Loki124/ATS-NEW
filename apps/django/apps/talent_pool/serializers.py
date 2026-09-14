"""Talent Pool Serializers (PRD v4 §14.7)"""
from rest_framework import serializers

from apps.field_acl.mixins import FieldAclSerializerMixin

from .models import TalentPoolEntry, TalentPoolTag


class TalentPoolTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentPoolTag
        fields = ['id', 'name', 'category', 'color', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TalentPoolEntryListSerializer(FieldAclSerializerMixin, serializers.ModelSerializer):
    """2026-08-03 R2 (寇豆码): 接上字段级 ACL。

    人才库列表把候选人手机号扁平化成 candidate_phone 直出明文,
    等于绕开了 Candidate 序列化器上的脱敏。
    """
    acl_entity = 'candidate'
    acl_strict = True  # HTTP API 序列化器: 即便意外没拿到 request context 也 fail-closed 脱敏

    candidate_name = serializers.CharField(source='candidate.name', read_only=True, default='')
    candidate_phone = serializers.CharField(source='candidate.phone', read_only=True, default='')
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    last_position_title = serializers.CharField(source='last_position.title', read_only=True, default='')
    last_stage_name = serializers.CharField(source='last_stage.name', read_only=True, default='')

    class Meta:
        model = TalentPoolEntry
        fields = [
            'id', 'candidate', 'candidate_name', 'candidate_phone',
            'source', 'source_display', 'source_detail',
            'last_position', 'last_position_title',
            'last_stage', 'last_stage_name',
            'tags', 'activated_count', 'last_activated_at',
            'is_active', 'created_at',
        ]


class TalentPoolEntryDetailSerializer(TalentPoolEntryListSerializer):
    class Meta(TalentPoolEntryListSerializer.Meta):
        fields = TalentPoolEntryListSerializer.Meta.fields + ['updated_at']


class TalentPoolEntryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentPoolEntry
        fields = [
            'candidate', 'source', 'source_detail',
            'last_position', 'last_stage', 'tags',
        ]
