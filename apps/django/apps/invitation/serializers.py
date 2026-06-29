"""Invitation Serializers (PRD v4 §14.6 邀约)"""
from rest_framework import serializers

from .models import Invitation


class InvitationListSerializer(serializers.ModelSerializer):
    inviter_name = serializers.CharField(source='inviter.username', read_only=True, default='')
    grabbed_by_name = serializers.CharField(source='grabbed_by.username', read_only=True, default='')
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    application_code = serializers.CharField(source='application.code', read_only=True, default='')

    class Meta:
        model = Invitation
        fields = [
            'id', 'application', 'application_code',
            'inviter', 'inviter_name',
            'invited_at', 'response_at', 'expire_at',
            'is_grab_pool', 'grabbed_by', 'grabbed_by_name', 'grabbed_at',
            'candidate_response', 'candidate_note',
            'state', 'state_display',
            'created_at',
        ]


class InvitationDetailSerializer(InvitationListSerializer):
    class Meta(InvitationListSerializer.Meta):
        fields = InvitationListSerializer.Meta.fields + ['updated_at']


class InvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = [
            'application', 'inviter', 'expire_at',
            'is_grab_pool',
        ]


class InvitationTransitionSerializer(serializers.Serializer):
    ACTION_CHOICES = [
        ('start_inviting', 'start_inviting'),
        ('succeed', 'succeed'),
        ('fail', 'fail'),
        ('timeout', 'timeout'),
    ]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    response = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
