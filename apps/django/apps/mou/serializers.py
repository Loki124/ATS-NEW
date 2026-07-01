"""mou serializers - 2026-07-01 修 PUT/POST

设计:
  - POST: FE 可传 id, 不传自动生成
  - PUT:  不需传 id (URL 已有)
  - GET:  返 snake_case (后端约定), FE 自己映射
"""
import re
import uuid
from rest_framework import serializers
from .models import MouAgreement, MouContainer, MutualExclusionGroup, AutomationRule


def _camel_to_snake(name):
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _convert_keys(data):
    if not isinstance(data, dict):
        return data
    return {_camel_to_snake(k): _convert_keys(v) for k, v in data.items()}


class _CamelCaseMixin:
    def to_internal_value(self, data):
        return super().to_internal_value(_convert_keys(data))


class MouContainerSerializer(_CamelCaseMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True)  # 2026-07-01: 不必填, create 时补

    class Meta:
        model = MouContainer
        fields = ['id', 'mou', 'code', 'position_title', 'quota_total', 'quota_used', 'created_at']

    def create(self, validated_data):
        if not validated_data.get('id'):
            validated_data['id'] = 'con_' + uuid.uuid4().hex[:12]
        return super().create(validated_data)


class MouAgreementSerializer(_CamelCaseMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True)  # 2026-07-01: POST/PUT 都可选
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

    def create(self, validated_data):
        if not validated_data.get('id'):
            validated_data['id'] = 'mou_' + uuid.uuid4().hex[:12]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('id', None)  # PUT 不更新 id
        return super().update(instance, validated_data)


class MutualExclusionGroupSerializer(_CamelCaseMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = MutualExclusionGroup
        fields = ['id', 'name', 'description', 'members', 'created_at']

    def create(self, validated_data):
        if not validated_data.get('id'):
            validated_data['id'] = 'mtx_' + uuid.uuid4().hex[:12]
        return super().create(validated_data)


class AutomationRuleSerializer(_CamelCaseMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = AutomationRule
        fields = ['id', 'name', 'trigger_event', 'conditions', 'actions', 'is_active', 'created_at', 'updated_at']

    def create(self, validated_data):
        if not validated_data.get('id'):
            validated_data['id'] = 'rule_' + uuid.uuid4().hex[:12]
        return super().create(validated_data)


class MouAuditLogSerializer(serializers.Serializer):
    id = serializers.CharField()
    actor = serializers.CharField()
    action = serializers.CharField()
    target = serializers.CharField()
    created_at = serializers.DateTimeField()
