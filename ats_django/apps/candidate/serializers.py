"""Candidate Serializers (PRD v4 §14.3)"""
from __future__ import annotations

from rest_framework import serializers

from apps.application.models import Application, ApplicationHistory, ApplicationStageRecord
from apps.core.models import User

from .models import Candidate, CandidateHistory, CandidateTag
from .services import CandidateCreateData, normalize_phone, validate_phone, validate_email, validate_id_card


# ============================================================
# Tag
# ============================================================
class CandidateTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateTag
        fields = ['id', 'name', 'color', 'category']


# ============================================================
# Candidate
# ============================================================
class CandidateListSerializer(serializers.ModelSerializer):
    """候选人列表 - 精简字段"""
    state_display = serializers.CharField(source='get_current_state_display', read_only=True)
    source_channel_name = serializers.CharField(
        source='source_channel.name', read_only=True, default='',
    )
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            'id', 'name', 'phone', 'email', 'gender', 'age',
            'current_state', 'state_display',
            'source_channel', 'source_channel_name',
            'referral_type', 'tags',
            'current_company', 'current_position',
            'created_at', 'application_count',
        ]

    def get_application_count(self, obj) -> int:
        return obj.applications.filter(deleted_at__isnull=True).count()


class CandidateHistorySerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.username', read_only=True, default='')

    class Meta:
        model = CandidateHistory
        fields = ['id', 'action', 'detail', 'operator', 'operator_name', 'created_at']


class CandidateDetailSerializer(serializers.ModelSerializer):
    """候选人详情"""
    state_display = serializers.CharField(source='get_current_state_display', read_only=True)
    source_channel_name = serializers.CharField(
        source='source_channel.name', read_only=True, default='',
    )
    referrer_name = serializers.CharField(source='referrer.username', read_only=True, default='')
    histories = CandidateHistorySerializer(many=True, read_only=True)
    applications = serializers.SerializerMethodField()
    soft_reject_stats = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            'id', 'name', 'phone', 'email', 'gender', 'age', 'birth_date', 'id_card_no',
            'highest_education', 'work_years',
            'current_city', 'expected_city', 'current_company', 'current_position',
            'expected_salary', 'resume_file_url', 'resume_text',
            'source_channel', 'source_channel_name',
            'referrer', 'referrer_name', 'referral_type',
            'resume_score', 'tags', 'current_state', 'state_display',
            'is_blacklisted', 'blacklist_reason',
            'moka_candidate_id', 'extra',
            'created_at', 'updated_at',
            'histories', 'applications', 'soft_reject_stats',
        ]
        read_only_fields = ['current_state', 'created_at', 'updated_at']

    def get_applications(self, obj):
        return [
            {
                'id': app.id,
                'code': app.code,
                'position_title': app.position.title if app.position else None,
                'state': app.state,
                'current_stage': app.current_stage.name if app.current_stage else None,
                'created_at': app.created_at.isoformat(),
            }
            for app in obj.applications.filter(deleted_at__isnull=True).order_by('-created_at')[:20]
        ]

    def get_soft_reject_stats(self, obj):
        from apps.application.services.soft_reject import SoftRejectService
        return SoftRejectService.get_soft_reject_stats(obj.id)


class CandidateCreateSerializer(serializers.Serializer):
    """创建候选人入参"""
    name = serializers.CharField(max_length=50)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True, max_length=8)
    age = serializers.IntegerField(required=False, allow_null=True)
    birth_date = serializers.DateField(required=False, allow_null=True)
    highest_education = serializers.CharField(required=False, allow_blank=True, max_length=50)
    work_years = serializers.DecimalField(required=False, allow_null=True, max_digits=4, decimal_places=1)
    current_city = serializers.CharField(required=False, allow_blank=True, max_length=50)
    expected_city = serializers.CharField(required=False, allow_blank=True, max_length=50)
    current_company = serializers.CharField(required=False, allow_blank=True, max_length=100)
    current_position = serializers.CharField(required=False, allow_blank=True, max_length=100)
    expected_salary = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=2)
    resume_file_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    resume_text = serializers.CharField(required=False, allow_blank=True)
    id_card_no = serializers.CharField(required=False, allow_blank=True, max_length=20)
    source_channel_id = serializers.CharField(required=False, allow_blank=True)
    referrer_id = serializers.CharField(required=False, allow_blank=True)
    referral_type = serializers.CharField(required=False, allow_blank=True, max_length=16)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    moka_candidate_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    extra = serializers.DictField(required=False)

    def validate_phone(self, value):
        try:
            return validate_phone(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_email(self, value):
        if not value:
            return value
        try:
            return validate_email(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_id_card_no(self, value):
        if not value:
            return value
        try:
            return validate_id_card(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def to_data(self) -> CandidateCreateData:
        return CandidateCreateData(
            name=self.validated_data['name'],
            phone=self.validated_data['phone'],
            **{k: v for k, v in self.validated_data.items() if k not in ('name', 'phone')},
        )


class CandidateUpdateSerializer(serializers.ModelSerializer):
    """更新候选人基本信息（不可改手机号/状态）"""
    class Meta:
        model = Candidate
        fields = [
            'email', 'gender', 'age', 'birth_date', 'id_card_no',
            'highest_education', 'work_years',
            'current_city', 'expected_city', 'current_company', 'current_position',
            'expected_salary', 'resume_file_url', 'resume_text',
            'tags', 'extra',
        ]


class CandidateStateTransitionSerializer(serializers.Serializer):
    """候选人状态转换入参"""
    ACTION_CHOICES = [
        ('enter_process', 'enter_process'),
        ('send_offer', 'send_offer'),
        ('mark_onboarded', 'mark_onboarded'),
        ('withdraw', 'withdraw'),
        ('move_to_talent_pool', 'move_to_talent_pool'),
        ('mark_process_failed', 'mark_process_failed'),
        ('pause_process', 'pause_process'),
        ('resume_process', 'resume_process'),
    ]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
    offer_id = serializers.CharField(required=False, allow_blank=True)
    onboarding_id = serializers.CharField(required=False, allow_blank=True)
    entry_source = serializers.CharField(required=False, allow_blank=True)
    extra = serializers.DictField(required=False)


class CandidateMergeSerializer(serializers.Serializer):
    """合并候选人"""
    primary_id = serializers.CharField()
    duplicate_ids = serializers.ListField(child=serializers.CharField())


class CandidateImportSerializer(serializers.Serializer):
    """批量导入"""
    candidates = serializers.ListField(child=CandidateCreateSerializer(), allow_empty=False)


class CandidateMokaSyncSerializer(serializers.Serializer):
    """摩卡同步"""
    moka_data = serializers.DictField()
