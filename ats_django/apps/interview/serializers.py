"""Interview Serializers (PRD v4 §14.5 面试)"""
from rest_framework import serializers

from .models import Interview, InterviewEvaluation


class InterviewListSerializer(serializers.ModelSerializer):
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    interviewers_names = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        fields = [
            'id', 'code', 'application', 'stage_record',
            'round_number', 'format', 'format_display',
            'scheduled_at', 'duration_minutes', 'location', 'meeting_url',
            'interviewers', 'interviewers_names',
            'status', 'status_display',
            'created_at',
        ]

    def get_interviewers_names(self, obj):
        return [u.username for u in obj.interviewers.all()]


class InterviewDetailSerializer(InterviewListSerializer):
    class Meta(InterviewListSerializer.Meta):
        fields = InterviewListSerializer.Meta.fields + ['updated_at']


class InterviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = [
            'application', 'stage_record', 'round_number', 'format',
            'scheduled_at', 'duration_minutes', 'location', 'meeting_url',
            'interviewers', 'status',
        ]


class InterviewEvaluationSerializer(serializers.ModelSerializer):
    interviewer_name = serializers.CharField(source='interviewer.username', read_only=True, default='')

    class Meta:
        model = InterviewEvaluation
        fields = [
            'id', 'interview', 'interviewer', 'interviewer_name',
            'scores', 'overall_score', 'recommendation', 'comment',
            'submitted_at',
        ]
        read_only_fields = ['id', 'submitted_at']
