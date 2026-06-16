"""Offer Serializers (PRD v4 §6.6, §14.5)"""
from rest_framework import serializers

from .models import Offer


class OfferListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.name', read_only=True, default='')
    position_title = serializers.CharField(source='position.title', read_only=True, default='')
    state_display = serializers.CharField(source='get_state_display', read_only=True)

    class Meta:
        model = Offer
        fields = [
            'id', 'code',
            'application', 'candidate', 'candidate_name',
            'position', 'position_title',
            'salary', 'salary_currency', 'level', 'position_title',
            'start_date', 'expire_date',
            'state', 'state_display',
            'sent_at', 'responded_at',
            'created_at',
        ]


class OfferDetailSerializer(OfferListSerializer):
    class Meta(OfferListSerializer.Meta):
        fields = OfferListSerializer.Meta.fields + [
            'approver', 'approved_at', 'rejection_reason', 'updated_at',
        ]


class OfferCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = [
            'application', 'candidate', 'position',
            'salary', 'salary_currency', 'level', 'position_title',
            'start_date', 'expire_date',
        ]


class OfferTransitionSerializer(serializers.Serializer):
    ACTION_CHOICES = [
        ('submit_approval', 'submit_approval'),
        ('approve', 'approve'),
        ('reject', 'reject'),
        ('send', 'send'),
        ('accept', 'accept'),
        ('negotiate', 'negotiate'),
        ('candidate_reject', 'candidate_reject'),
        ('onboarded', 'onboarded'),
    ]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
