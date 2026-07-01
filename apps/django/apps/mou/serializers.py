"""mou serializers - 2026-07-01 stub"""
from rest_framework import serializers
from .models import MouAgreement, MouContainer, MutualExclusionGroup, AutomationRule


class MouContainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MouContainer
        fields = ['id', 'mou', 'code', 'position_title', 'quota_total', 'quota_used', 'created_at']


class MouAgreementSerializer(serializers.ModelSerializer):
    containers = MouContainerSerializer(many=True, read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    quota_total = serializers.SerializerMethodField()
    quota_used = serializers.SerializerMethodField()

    class Meta:
        model = MouAgreement
        fields = ['id', 'code', 'company_name', 'department', 'department_name', 'signed_at',
                  'effective_at', 'expire_at', 'status', 'owner', 'owner_name', 'terms',
                  'containers', 'quota_total', 'quota_used', 'created_at', 'updated_at']

    def get_quota_total(self, obj):
        return sum(c.quota_total for c in obj.containers.all())

    def get_quota_used(self, obj):
        return sum(c.quota_used for c in obj.containers.all())


class MutualExclusionGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MutualExclusionGroup
        fields = ['id', 'name', 'description', 'members', 'created_at']


class AutomationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRule
        fields = ['id', 'name', 'trigger_event', 'conditions', 'actions', 'is_active', 'created_at', 'updated_at']


class MouAuditLogSerializer(serializers.Serializer):
    """审计日志从 audit app 拿, 这里只返空 stub (避免跨 app 依赖)"""
    id = serializers.CharField()
    actor = serializers.CharField()
    action = serializers.CharField()
    target = serializers.CharField()
    created_at = serializers.DateTimeField()
