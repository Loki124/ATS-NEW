"""Entry Condition Serializers (PRD v4 §10)"""
from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from apps.process.models import ProcessStageLink

from .models import (
    ConditionItem,
    EntryConditionLog,
    EntryConditionRule,
)


class ConditionItemSerializer(serializers.ModelSerializer):
    """条件项"""
    condition_type_display = serializers.CharField(source='get_condition_type_display', read_only=True)
    operator_display = serializers.CharField(source='get_operator_display', read_only=True)

    class Meta:
        model = ConditionItem
        fields = [
            'id', 'rule',
            'item_seq',
            'condition_type', 'condition_type_display',
            'field',
            'stage_name', 'stage_statuses',
            'operator', 'operator_display',
            'value', 'auto_filter_inactive_users',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConditionItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionItem
        fields = [
            'id', 'item_seq', 'condition_type', 'field',
            'stage_name', 'stage_statuses',
            'operator', 'value', 'auto_filter_inactive_users',
        ]
        read_only_fields = ['id']


class EntryConditionRuleSerializer(serializers.ModelSerializer):
    """进入条件规则"""
    items = ConditionItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    link_id = serializers.CharField(source='link.id', read_only=True)
    stage_name = serializers.CharField(source='link.stage.name', read_only=True)

    class Meta:
        model = EntryConditionRule
        fields = [
            'id', 'link', 'link_id', 'stage_name',
            'process_id', 'workflow_version',
            'rule_name', 'rule_seq', 'status', 'status_display',
            'expression', 'reject_message',
            'match_type',
            'items',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]
        read_only_fields = ['id', 'process_id', 'workflow_version', 'created_at', 'updated_at', 'created_by', 'updated_by']

    def validate_rule_name(self, value):
        if len(value) > 30:
            raise serializers.ValidationError('规则名称不可超过 30 字')
        return value.strip()

    def validate_expression(self, value):
        if not value or not value.strip():
            return '1'
        return value.strip()


class EntryConditionRuleCreateSerializer(serializers.ModelSerializer):
    """创建/更新规则 - 嵌套 items（写接口统一用 link_id，与读接口的 link_id 对齐）"""
    items = ConditionItemCreateSerializer(many=True)
    # 写接口用 link_id（与读接口 EntryConditionRuleSerializer.link_id 对齐），映射到 link FK。
    # required=False：创建时必填（create() 缺它会报错），更新时无需传、沿用原关联。
    link_id = serializers.PrimaryKeyRelatedField(
        queryset=ProcessStageLink.objects.all(), source='link',
        required=False, help_text='流程-阶段关联 ID（创建时必填，更新时无需传）',
    )

    class Meta:
        model = EntryConditionRule
        fields = [
            'id', 'link_id', 'rule_name', 'rule_seq', 'status',
            'expression', 'reject_message', 'items',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        link = attrs.get('link')
        items = attrs.get('items', [])
        # 创建时必须指定 link；更新时沿用已有关联（instance 已存在）
        if self.instance is None and link is None:
            raise serializers.ValidationError({'link_id': '创建进入条件规则时必须提供 link_id'})
        if link and items:
            # 校验 item_seq 唯一
            seqs = [i['item_seq'] for i in items]
            if len(seqs) != len(set(seqs)):
                raise serializers.ValidationError({'items': '条件序号必须唯一'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request = self.context.get('request')
        actor = request.user if request and request.user.is_authenticated else None

        link = validated_data['link']
        # 自动填充 process_id 和 version
        validated_data['process_id'] = link.process_id
        validated_data['workflow_version'] = link.process.current_version

        rule = EntryConditionRule.objects.create(
            **validated_data,
            created_by=actor,
            updated_by=actor,
        )
        for item_data in items_data:
            ConditionItem.objects.create(rule=rule, **item_data)
        return rule

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        request = self.context.get('request')
        actor = request.user if request and request.user.is_authenticated else None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = actor
        instance.save()

        if items_data is not None:
            # 全量替换
            instance.items.all().delete()
            for item_data in items_data:
                ConditionItem.objects.create(rule=instance, **item_data)
        return instance


class EntryConditionLogSerializer(serializers.ModelSerializer):
    """评估日志"""
    rule_name = serializers.CharField(source='rule.rule_name', read_only=True)

    class Meta:
        model = EntryConditionLog
        fields = [
            'id', 'rule', 'rule_name',
            'candidate_id', 'stage_id', 'link_id',
            'passed', 'reject_message', 'snapshot',
            'created_at',
        ]
        read_only_fields = fields


class EntryConditionEvaluateRequestSerializer(serializers.Serializer):
    """评估请求"""
    candidate_id = serializers.CharField()
    demand_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    link_id = serializers.CharField(required=False, help_text='可选，不传则用 link_id')


class EntryConditionEvaluateResponseSerializer(serializers.Serializer):
    """评估响应"""
    overall_passed = serializers.BooleanField()
    matched_rule_seq = serializers.IntegerField(allow_null=True)
    reject_message = serializers.CharField(allow_blank=True)
    stage_id = serializers.CharField()
    stage_name = serializers.CharField()
    rule_results = serializers.ListField(child=serializers.DictField())


class EntryConditionRuleReorderSerializer(serializers.Serializer):
    """规则重新排序"""
    rule_orders = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        help_text='[{"rule_id": "...", "rule_seq": 1}, ...]',
    )
