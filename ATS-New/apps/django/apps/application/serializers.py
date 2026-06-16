"""Application Serializers (PRD v4 §6, §13, §14.4)"""
from __future__ import annotations

from rest_framework import serializers

from apps.candidate.serializers import CandidateListSerializer
from apps.position.serializers import PositionListSerializer
from apps.process.serializers import (
    RecruitmentProcessDetailSerializer,
    RecruitmentStageSerializer,
)

from .models import Application, ApplicationHistory, ApplicationStageRecord


# ============================================================
# Stage Record
# ============================================================
class ApplicationStageRecordSerializer(serializers.ModelSerializer):
    """阶段记录"""
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    stage_type = serializers.CharField(source='stage.stage_type', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    duration_days_computed = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationStageRecord
        fields = [
            'id', 'application', 'link', 'stage', 'stage_name', 'stage_type',
            'state', 'state_display',
            'entered_at', 'exited_at', 'duration_days', 'duration_days_computed',
            'time_limit_rule_id', 'total_time_limit_days', 'deadline', 'is_overdue',
            'current_handlers', 'auto_promoted', 'automation_rule_id',
            'note', 'created_at',
        ]
        read_only_fields = fields

    def get_duration_days_computed(self, obj) -> int:
        if obj.exited_at and obj.entered_at:
            return max(0, (obj.exited_at - obj.entered_at).days)
        return obj.duration_days or 0

    def get_is_overdue(self, obj) -> bool:
        from django.utils import timezone
        if obj.state in (
            ApplicationStageRecord.StageState.PASSED,
            ApplicationStageRecord.StageState.FAILED,
            ApplicationStageRecord.StageState.ARCHIVED,
            ApplicationStageRecord.StageState.SKIPPED,
            ApplicationStageRecord.StageState.REJECTED,
            ApplicationStageRecord.StageState.TIMEOUT,
        ):
            return False
        if obj.deadline:
            return timezone.now() > obj.deadline
        return False


# ============================================================
# Application
# ============================================================
class ApplicationListSerializer(serializers.ModelSerializer):
    """申请列表"""
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    candidate_phone = serializers.CharField(source='candidate.phone', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    position_code = serializers.CharField(source='position.code', read_only=True)
    process_name = serializers.CharField(source='process.name', read_only=True)
    current_stage_name = serializers.CharField(source='current_stage.name', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    is_in_grab_pool = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'code', 'candidate', 'candidate_name', 'candidate_phone',
            'position', 'position_code', 'position_title',
            'process', 'process_name', 'workflow_version',
            'current_link', 'current_stage', 'current_stage_name',
            'state', 'state_display',
            'stage_entered_at', 'stage_deadline', 'is_overdue',
            'total_time_limit_days',
            'is_grabbed', 'grabbed_by', 'grabbed_at', 'is_in_grab_pool',
            'created_at', 'last_advanced_at',
        ]

    def get_is_overdue(self, obj) -> bool:
        from django.utils import timezone
        if not obj.stage_deadline:
            return False
        if obj.state in ('ONBOARDED', 'WITHDRAWN', 'TIMEOUT', 'REJECTED'):
            return False
        return timezone.now() > obj.stage_deadline

    def get_is_in_grab_pool(self, obj) -> bool:
        return (
            obj.state == Application.ApplicationState.ACTIVE
            and not obj.is_grabbed
            and obj.current_link
            and getattr(obj.current_link, 'stage_rule', None)
            and obj.current_link.stage_rule.is_grab_mode
        )


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """申请详情"""
    candidate = CandidateListSerializer(read_only=True)
    position = PositionListSerializer(read_only=True)
    process = RecruitmentProcessDetailSerializer(read_only=True)
    current_stage = RecruitmentStageSerializer(read_only=True)
    current_stage_records = serializers.SerializerMethodField()
    all_records = serializers.SerializerMethodField()
    histories = serializers.SerializerMethodField()
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    grabbed_by_name = serializers.CharField(source='grabbed_by.username', read_only=True, default='')
    is_overdue = serializers.SerializerMethodField()
    soft_reject_count = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'code',
            'candidate', 'position', 'process', 'workflow_version',
            'current_link', 'current_stage', 'current_stage_records', 'all_records',
            'state', 'state_display', 'histories',
            'time_limit_rule_id', 'total_time_limit_days',
            'stage_entered_at', 'stage_deadline', 'is_overdue',
            'is_grabbed', 'grabbed_by', 'grabbed_by_name', 'grabbed_at',
            'soft_reject_count',
            'last_advanced_at', 'created_at', 'updated_at',
        ]

    def get_current_stage_records(self, obj):
        if not obj.current_link:
            return []
        recs = obj.stage_records.filter(
            link=obj.current_link, deleted_at__isnull=True,
        ).order_by('-entered_at')
        return ApplicationStageRecordSerializer(recs, many=True).data

    def get_all_records(self, obj):
        recs = obj.stage_records.filter(deleted_at__isnull=True).order_by('entered_at')
        return ApplicationStageRecordSerializer(recs, many=True).data

    def get_histories(self, obj):
        histories = obj.histories.filter(deleted_at__isnull=True).order_by('-created_at')[:50]
        return ApplicationHistorySerializer(histories, many=True).data

    def get_is_overdue(self, obj) -> bool:
        from django.utils import timezone
        if not obj.stage_deadline:
            return False
        if obj.state in ('ONBOARDED', 'WITHDRAWN', 'TIMEOUT', 'REJECTED'):
            return False
        return timezone.now() > obj.stage_deadline

    def get_soft_reject_count(self, obj) -> int:
        from apps.application.services.soft_reject import SoftRejectService
        return SoftRejectService.count_soft_rejects(obj)


class ApplicationCreateSerializer(serializers.Serializer):
    """创建申请入参"""
    candidate_id = serializers.CharField()
    position_id = serializers.CharField()
    process_id = serializers.CharField(required=False, allow_blank=True)
    initial_stage_id = serializers.CharField(required=False, allow_blank=True)
    extra = serializers.DictField(required=False)


class ApplicationHistorySerializer(serializers.ModelSerializer):
    from_stage_name = serializers.CharField(source='from_stage.name', read_only=True, default='')
    to_stage_name = serializers.CharField(source='to_stage.name', read_only=True, default='')
    operator_name = serializers.CharField(source='operator.username', read_only=True, default='')

    class Meta:
        model = ApplicationHistory
        fields = [
            'id', 'application', 'action',
            'from_stage', 'from_stage_name',
            'to_stage', 'to_stage_name',
            'detail', 'operator', 'operator_name', 'is_auto',
            'created_at',
        ]


class ApplicationAdvanceSerializer(serializers.Serializer):
    """推进申请"""
    reason = serializers.CharField(required=False, allow_blank=True)
    skip_entry_condition = serializers.BooleanField(default=False)


class ApplicationJumpSerializer(serializers.Serializer):
    """跳到指定阶段"""
    target_stage_id = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True)
    skip_entry_condition = serializers.BooleanField(default=False)


class ApplicationSoftRejectSerializer(serializers.Serializer):
    """软拒"""
    reason = serializers.CharField()


class ApplicationWithdrawSerializer(serializers.Serializer):
    """撤回"""
    reason = serializers.CharField()


class ApplicationPauseSerializer(serializers.Serializer):
    """暂停"""
    reason = serializers.CharField(required=False, allow_blank=True)


class ApplicationGrabSerializer(serializers.Serializer):
    """抢单"""
    pass


class ApplicationReleaseSerializer(serializers.Serializer):
    """释放抢单"""
    reason = serializers.CharField(required=False, allow_blank=True)


class GrabPoolQuerySerializer(serializers.Serializer):
    """抢单池查询"""
    stage_id = serializers.CharField(required=False, allow_blank=True)
    position_id = serializers.CharField(required=False, allow_blank=True)
    limit = serializers.IntegerField(default=50, min_value=1, max_value=200)


class InvitationCreateSerializer(serializers.Serializer):
    """创建邀请入参"""
    application_id = serializers.CharField()
    channel = serializers.ChoiceField(
        choices=['EMAIL', 'SMS', 'WECOM', 'IN_APP'],
        default='EMAIL',
    )
    template_code = serializers.CharField(required=False, allow_blank=True)
    custom_message = serializers.CharField(required=False, allow_blank=True)
    expires_hours = serializers.IntegerField(default=72, min_value=1, max_value=720)


class InvitationRespondSerializer(serializers.Serializer):
    """候选人响应"""
    code = serializers.CharField()
    accept = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True)
