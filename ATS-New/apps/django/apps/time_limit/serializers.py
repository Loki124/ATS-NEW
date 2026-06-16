"""Time Limit Serializers"""
from rest_framework import serializers

from .models import TimeLimitRule


class TimeLimitRuleSerializer(serializers.ModelSerializer):
    """阶段限时规则"""
    effective_scope_display = serializers.SerializerMethodField()
    link_id = serializers.CharField(source='link.id', read_only=True)
    stage_name = serializers.CharField(source='link.stage.name', read_only=True)
    process_name = serializers.CharField(source='link.process.name', read_only=True)

    class Meta:
        model = TimeLimitRule
        fields = [
            'id', 'link', 'link_id', 'stage_name', 'process_name',
            'process_id', 'workflow_version',
            'rule_name', 'conditions',
            'lock_duration', 'extension_per_person',
            'effective_scope', 'effective_scope_display',
            'priority', 'enabled',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]
        read_only_fields = [
            'id', 'process_id', 'workflow_version',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]

    def get_effective_scope_display(self, obj):
        return obj.get_effective_scope_display() if hasattr(obj, 'get_effective_scope_display') else obj.effective_scope

    def validate_lock_duration(self, value):
        if value < 1 or value > 365:
            raise serializers.ValidationError('锁定时长必须在 1-365 天之间')
        return value

    def validate_extension_per_person(self, value):
        if value < 0 or value > 30:
            raise serializers.ValidationError('加时规则必须在 0-30 天/人之间')
        return value

    def validate_conditions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('conditions 必须是数组')
        return value


class TimeLimitCalculateRequestSerializer(serializers.Serializer):
    """限时计算请求"""
    link_id = serializers.CharField()
    candidate_id = serializers.CharField()
    interviewer_count = serializers.IntegerField(default=1, min_value=1, max_value=50)
    workflow_version = serializers.CharField(required=False, allow_blank=True)


class TimeLimitCalculateResponseSerializer(serializers.Serializer):
    """限时计算响应"""
    matched = serializers.BooleanField()
    rule_id = serializers.CharField(allow_null=True)
    rule_name = serializers.CharField()
    base_lock_days = serializers.IntegerField()
    extension_days = serializers.IntegerField()
    extra_interviewer_days = serializers.IntegerField()
    total_lock_days = serializers.IntegerField()
    effective_scope = serializers.CharField()
    locked_until = serializers.CharField(allow_null=True)
