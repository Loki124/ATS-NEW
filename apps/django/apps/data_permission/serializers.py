"""数据权限规则序列化器。

项目全局启用 djangorestframework-camel-case, 此处一律用 snake_case 字段名,
API 层自动转 camelCase (前端契约: dimensionType / dimensionValue / scopeType ...)。
"""
from rest_framework import serializers

from .expr_compiler import validate_scope_payload
from .models import DataPermissionRule, RowScopeType


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

    def validate(self, attrs):
        scope_type = attrs.get('scope_type')
        payload = attrs.get('scope_payload')
        if scope_type == RowScopeType.CUSTOM:
            if not isinstance(payload, dict):
                raise serializers.ValidationError({'scope_payload': 'CUSTOM 范围需为对象'})
            if 'groups' in payload:
                # 新格式（数据权限向导）：{expr, groups}
                entity = attrs.get('entity')
                if not entity:
                    raise serializers.ValidationError(
                        {'entity': 'CUSTOM 表达式范围需指定 entity（业务模块 key）'})
                reason = validate_scope_payload(payload, entity)
                if reason:
                    raise serializers.ValidationError({'scope_payload': reason})
            else:
                # 兼容旧格式 {"department_ids":[...]} / {"management_unit_ids":[...]}
                if not (payload.get('department_ids') or payload.get('management_unit_ids')):
                    raise serializers.ValidationError(
                        {'scope_payload': 'CUSTOM 范围需提供 groups 或 department_ids/management_unit_ids'})
        return attrs
