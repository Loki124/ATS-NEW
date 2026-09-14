"""数据权限规则序列化器。

项目全局启用 djangorestframework-camel-case, 此处一律用 snake_case 字段名,
API 层自动转 camelCase (前端契约: dimensionType / dimensionValue / scopeType ...)。
"""
from rest_framework import serializers

from .models import DataPermissionRule


class DataPermissionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataPermissionRule
        fields = [
            'id',
            'dimension_type', 'dimension_value', 'level',
            'scope_type', 'scope_payload',
            'entity', 'field', 'permission',
            'priority', 'status', 'remark', 'created_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
