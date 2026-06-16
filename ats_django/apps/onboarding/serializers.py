"""Onboarding Serializers (PRD v4 §6.7)"""
from rest_framework import serializers

from .models import Onboarding


class OnboardingListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.name', read_only=True, default='')
    position_title = serializers.CharField(source='position.title', read_only=True, default='')
    state_display = serializers.CharField(source='get_state_display', read_only=True)

    class Meta:
        model = Onboarding
        fields = [
            'id', 'offer', 'candidate', 'candidate_name',
            'position', 'position_title',
            'start_date', 'actual_start_date', 'probation_end_date',
            'state', 'state_display',
            'regularization_result', 'regularization_at',
            'created_at',
        ]


class OnboardingDetailSerializer(OnboardingListSerializer):
    class Meta(OnboardingListSerializer.Meta):
        fields = OnboardingListSerializer.Meta.fields + ['todo_list', 'todo_completed', 'updated_at']


class OnboardingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Onboarding
        fields = [
            'offer', 'candidate', 'position',
            'start_date', 'actual_start_date', 'probation_end_date',
        ]


class OnboardingTransitionSerializer(serializers.Serializer):
    ACTION_CHOICES = [
        ('start_preparing', 'start_preparing'),
        ('complete', 'complete'),
        ('delay', 'delay'),
        ('resume', 'resume'),
        ('enter_probation', 'enter_probation'),
        ('regularize', 'regularize'),
    ]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    new_date = serializers.DateField(required=False)
    result = serializers.CharField(required=False, default='PASS')
