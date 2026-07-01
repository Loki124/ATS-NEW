"""mou serializers - 2026-07-01 GET/PUT/POST 全部 camelCase

设计:
  - POST: FE 可传 id, 不传自动生成; body camelCase/snake_case 都接
  - PUT:  不需传 id (URL 已有); body camelCase/snake_case 都接
  - GET:  输出全部 camelCase (FE 期望)
"""
import re
import uuid
from rest_framework import serializers
from .models import MouAgreement, MouContainer, MutualExclusionGroup, AutomationRule


def _camel_to_snake(name):
    """companyName → company_name, triggerEvent → trigger_event"""
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _snake_to_camel(name):
    """company_name → companyName, created_at → createdAt"""
    parts = name.split('_')
    return parts[0] + ''.join(p.title() for p in parts[1:])


def _convert_keys_to_snake(data):
    """dict key camelCase → snake_case (递归 input)"""
    if not isinstance(data, dict):
        return data
    return {_camel_to_snake(k): _convert_keys_to_snake(v) for k, v in data.items()}


def _convert_keys_to_camel(data):
    """dict key snake_case → camelCase (递归 output)"""
    if isinstance(data, list):
        return [_convert_keys_to_camel(item) for item in data]
    if not isinstance(data, dict):
        return data
    out = {}
    for k, v in data.items():
        # id / url 这种不转, 但 _id 也转 (mouId)
        new_k = _snake_to_camel(k) if ('_' in k) else k
        out[new_k] = _convert_keys_to_camel(v)
    return out


class _CamelCaseSerializerMixin:
    """input: camelCase → snake_case, output: snake_case → camelCase"""

    def to_internal_value(self, data):
        return super().to_internal_value(_convert_keys_to_snake(data))

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        return _convert_keys_to_camel(ret)


class MouContainerSerializer(_CamelCaseSerializerMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True, read_only=True)

    class Meta:
        model = MouContainer
        fields = ['id', 'mou', 'code', 'position_title', 'quota_total', 'quota_used', 'created_at']

    def create(self, validated_data):
        if not validated_data.get('id'):
            validated_data['id'] = 'con_' + uuid.uuid4().hex[:12]
        return super().create(validated_data)


class MouAgreementSerializer(_CamelCaseSerializerMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True, read_only=True)
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
        validated_data.pop('id', None)
        return super().update(instance, validated_data)


class MutualExclusionGroupSerializer(_CamelCaseSerializerMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True, read_only=True)

    class Meta:
        model = MutualExclusionGroup
        fields = ['id', 'name', 'description', 'members', 'created_at']

    def create(self, validated_data):
        if not validated_data.get('id'):
            validated_data['id'] = 'mtx_' + uuid.uuid4().hex[:12]
        return super().create(validated_data)


class AutomationRuleSerializer(_CamelCaseSerializerMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True, read_only=True)

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
