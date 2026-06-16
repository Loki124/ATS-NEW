"""Automation Serializers"""
from rest_framework import serializers

from .models import AutomationLog, AutomationRule


class AutomationRuleSerializer(serializers.ModelSerializer):
    """自动化规则"""
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)
    trigger_timing_display = serializers.CharField(source='get_trigger_timing_display', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    condition_logic_display = serializers.CharField(source='get_condition_logic_display', read_only=True)

    process_name = serializers.CharField(source='process.name', read_only=True)
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    next_stage_name = serializers.CharField(source='next_stage.name', read_only=True)

    class Meta:
        model = AutomationRule
        fields = [
            'id', 'name',
            'process', 'process_name',
            'stage', 'stage_name',
            'trigger_type', 'trigger_type_display',
            'trigger_timing', 'trigger_timing_display',
            'trigger_delay_hours',
            'condition_logic', 'condition_logic_display',
            'condition_json',
            'action_type', 'action_type_display',
            'next_stage', 'next_stage_name',
            'skip_check',
            'scope_json',
            'priority', 'priority_display',
            'enabled', 'failure_rate_threshold',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by', 'updated_by',
        ]

    def validate_condition_json(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('condition_json 必须是数组')
        return value

    def validate_scope_json(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('scope_json 必须是对象')
        return value

    def validate(self, attrs):
        timing = attrs.get('trigger_timing')
        delay = attrs.get('trigger_delay_hours')
        if timing == 'DELAY' and (delay is None or delay < 1):
            raise serializers.ValidationError(
                {'trigger_delay_hours': '延迟执行必须指定延迟小时数 (≥ 1)'},
            )
        action = attrs.get('action_type')
        next_stage = attrs.get('next_stage')
        if action == 'SKIP_TO' and not next_stage:
            raise serializers.ValidationError(
                {'next_stage': 'SKIP_TO 动作必须指定目标阶段'},
            )
        return attrs


class AutomationLogSerializer(serializers.ModelSerializer):
    """自动化执行日志"""
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    evaluate_result_display = serializers.CharField(source='get_evaluate_result_display', read_only=True)

    class Meta:
        model = AutomationLog
        fields = [
            'id', 'rule', 'rule_name',
            'candidate_id',
            'trigger_time',
            'evaluate_result', 'evaluate_result_display',
            'action_taken', 'skip_reason', 'error_message', 'execution_ms',
        ]
        read_only_fields = fields


class AutomationTriggerRequestSerializer(serializers.Serializer):
    """手动触发"""
    trigger_type = serializers.ChoiceField(choices=AutomationRule.TriggerType.choices)
    candidate_id = serializers.CharField()
    application_id = serializers.CharField(required=False, allow_blank=True)
    stage_id = serializers.CharField(required=False, allow_blank=True)
    extra = serializers.JSONField(required=False, default=dict)
