"""Demand Serializers (PRD v4 §14.1)"""
from rest_framework import serializers

from .models import Demand, DemandApproval


class DemandListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True, default='')
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True, default='')
    hr_name = serializers.CharField(source='hr.username', read_only=True, default='')
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    headcount_remaining = serializers.SerializerMethodField()
    position_count = serializers.SerializerMethodField()

    class Meta:
        model = Demand
        fields = [
            'id', 'code', 'title',
            'department', 'department_name',
            'requested_by', 'requested_by_name',
            'hr', 'hr_name',
            'headcount', 'filled_count', 'headcount_remaining',
            'level', 'position_title',
            'process', 'process_version',
            'state', 'state_display', 'priority',
            'submitted_at', 'approved_at',
            'position_count',
            'created_at',
        ]

    def get_headcount_remaining(self, obj) -> int:
        return max(0, obj.headcount - obj.filled_count)

    def get_position_count(self, obj) -> int:
        return obj.positions.filter(deleted_at__isnull=True).count() if hasattr(obj, 'positions') else 0


class DemandDetailSerializer(DemandListSerializer):
    class Meta(DemandListSerializer.Meta):
        fields = DemandListSerializer.Meta.fields + [
            'jd', 'requirements', 'updated_at',
        ]


class DemandCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Demand
        fields = [
            'title', 'department', 'requested_by', 'hr',
            'headcount', 'level', 'position_title',
            'process', 'process_version',
            'jd', 'requirements', 'priority',
        ]


class DemandTransitionSerializer(serializers.Serializer):
    """需求状态转换"""
    ACTION_CHOICES = [
        ('submit', 'submit'),
        ('approve', 'approve'),
        ('reject', 'reject'),
        ('start_recruiting', 'start_recruiting'),
        ('pause', 'pause'),
        ('resume', 'resume'),
        ('complete', 'complete'),
        ('cancel', 'cancel'),
    ]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)


class DemandApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source='approver.username', read_only=True, default='')

    class Meta:
        model = DemandApproval
        fields = [
            'id', 'demand', 'approver', 'approver_name',
            'level', 'result', 'comment',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
