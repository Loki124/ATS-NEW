"""mou serializers - 2026-07-01 修 PUT 400 (mouType null 兜底)"""
import re
import uuid

from rest_framework import serializers

from .models import MouAgreement, MouContainer, MouRule, MutualExclusionGroup


def _camel_to_snake(name):
    s1 = re.sub(r'(.)([A-Z][a-z]+)', chr(92) + chr(49) + chr(92) + chr(50), name)
    return re.sub(r'([a-z0-9])([A-Z])', chr(92) + chr(49) + chr(92) + chr(50), s1).lower()


def _snake_to_camel(name):
    parts = name.split('_')
    return parts[0] + ''.join(p.title() for p in parts[1:])


def _convert_keys_to_snake(data):
    if not isinstance(data, dict):
        return data
    return {_camel_to_snake(k): _convert_keys_to_snake(v) for k, v in data.items()}


def _convert_keys_to_camel(data):
    if isinstance(data, list):
        return [_convert_keys_to_camel(item) for item in data]
    if not isinstance(data, dict):
        return data
    out = {}
    for k, v in data.items():
        new_k = _snake_to_camel(k) if ('_' in k) else k
        out[new_k] = _convert_keys_to_camel(v)
    return out


class _CamelCaseSerializerMixin:
    def to_internal_value(self, data):
        return super().to_internal_value(_convert_keys_to_snake(data))

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        return _convert_keys_to_camel(ret)


class MouContainerSerializer(_CamelCaseSerializerMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True, read_only=True)
    # 2026-07-02: FE 字段名兼容 — 接受 status (前端) / quota_status (model) 两种叫法
    quota_status = serializers.CharField(required=False, allow_blank=True, default='ACTIVE')

    class Meta:
        model = MouContainer
        fields = ['id', 'mou', 'code', 'position_title', 'type', 'description',
                  'resource_filter', 'quota_total', 'quota_used', 'quota_status',
                  'created_at']

    def to_internal_value(self, data):
        converted = _convert_keys_to_snake(data) if isinstance(data, dict) else data
        if isinstance(converted, dict):
            # 2026-07-02: FE 字段名兼容
            #   FE 送 mouId (camelCase, FK 标识), 后端字段叫 mou
            if 'mou_id' in converted and 'mou' not in converted:
                converted['mou'] = converted.pop('mou_id')
            #   FE 用 name 表示职位名, 后端字段叫 position_title
            if 'name' in converted and 'position_title' not in converted:
                converted['position_title'] = converted.pop('name')
            #   FE 送 status, 后端字段叫 quota_status
            if 'status' in converted and 'quota_status' not in converted:
                converted['quota_status'] = converted.pop('status')
        return super().to_internal_value(converted)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # FE 期待 mouId / name / status (跟 form 字段一致)
        # 注意: _CamelCaseSerializerMixin.to_representation 已把 keys 转成 camelCase
        ret['mouId'] = ret.get('mou')
        ret['name'] = ret.get('positionTitle')
        ret['status'] = ret.get('quotaStatus')
        return ret

    def create(self, validated_data):
        if not validated_data.get('id'):
            validated_data['id'] = 'con_' + uuid.uuid4().hex[:12]
        return super().create(validated_data)


class MouAgreementSerializer(_CamelCaseSerializerMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True, read_only=True)
    company_name = serializers.CharField(required=False, allow_blank=True, default='')
    scopes = serializers.JSONField(required=False, default=dict)
    # 2026-07-01: mou_type 接受空/null, 兜底 STANDARD
    # CharField 默认可接受空字符串 (allow_blank=True), 不允许 null
    # 单独处理 null
    mou_type = serializers.CharField(required=False, allow_blank=True, default='STANDARD')

    containers = MouContainerSerializer(many=True, read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    quota_total = serializers.SerializerMethodField()
    quota_used = serializers.SerializerMethodField()

    class Meta:
        model = MouAgreement
        fields = ['id', 'code', 'company_name', 'department', 'department_name', 'signed_at',
                  'effective_at', 'expire_at', 'status', 'owner', 'owner_name', 'terms',
                  'mou_type', 'scopes',
                  'containers', 'quota_total', 'quota_used', 'created_at', 'updated_at']

    def get_quota_total(self, obj):
        return sum(c.quota_total for c in obj.containers.all())

    def get_quota_used(self, obj):
        return sum(c.quota_used for c in obj.containers.all())

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['name'] = instance.company_name
        ret['description'] = instance.terms
        ret['mouType'] = instance.mou_type
        return ret

    def to_internal_value(self, data):
        converted = _convert_keys_to_snake(data) if isinstance(data, dict) else data
        if isinstance(converted, dict):
            # mouType null 兜底
            if converted.get('mou_type') is None:
                converted['mou_type'] = 'STANDARD'
            if 'name' in converted and 'company_name' not in converted:
                converted['company_name'] = converted.pop('name')
            if 'description' in converted and 'terms' not in converted:
                converted['terms'] = converted.pop('description')
            if 'mouType' in converted and 'mou_type' not in converted:
                converted['mou_type'] = converted.pop('mouType')
        return super().to_internal_value(converted)

    def create(self, validated_data):
        if not validated_data.get('id'):
            validated_data['id'] = 'mou_' + uuid.uuid4().hex[:12]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('id', None)
        if 'name' in validated_data and 'company_name' not in validated_data:
            validated_data['company_name'] = validated_data.pop('name')
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


class MouRuleSerializer(_CamelCaseSerializerMixin, serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_blank=True, read_only=True)

    class Meta:
        model = MouRule
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
