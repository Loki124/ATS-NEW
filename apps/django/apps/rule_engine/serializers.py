"""统一规则只读序列化器（Phase 1）。

仅序列化 UnifiedRuleDTO（不绑定 DB 模型）。出参经 CamelCaseJSONRenderer 自动转驼峰。
严格只读：无写逻辑。
"""
from rest_framework import serializers


class UnifiedRuleSerializer(serializers.Serializer):
    """统一规则 DTO 只读序列化器。

    字段对齐 UnifiedRuleDTO；conditions_summary / actions_summary / scope_json /
    config_json 用 JSONField 透传（均为 list/dict）。
    """

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    source_app = serializers.CharField(read_only=True)
    trigger_type = serializers.CharField(read_only=True)
    legacy_model = serializers.CharField(read_only=True)
    legacy_id = serializers.CharField(read_only=True)

    trigger_timing = serializers.CharField(required=False, allow_null=True)
    scope_json = serializers.JSONField(required=False)
    priority = serializers.CharField(required=False)
    priority_rank = serializers.IntegerField(required=False, default=0)
    status = serializers.CharField(required=False)
    enabled = serializers.BooleanField(required=False, default=True)
    condition_expression = serializers.CharField(required=False, allow_blank=True)
    condition_logic = serializers.CharField(required=False, allow_blank=True)
    config_json = serializers.JSONField(required=False)

    conditions_summary = serializers.JSONField(required=False)
    actions_summary = serializers.JSONField(required=False)
