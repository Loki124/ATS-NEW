"""Referral Serializers (PRD v4 §3.1, §6.4 N+1/N+2)"""
from rest_framework import serializers

from .models import Referral


class ReferralListSerializer(serializers.ModelSerializer):
    referrer_name = serializers.CharField(source='referrer.username', read_only=True, default='')
    candidate_name = serializers.CharField(source='candidate.name', read_only=True, default='')
    position_title = serializers.CharField(source='position.title', read_only=True, default='')
    referral_type_display = serializers.CharField(source='get_referral_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Referral
        fields = [
            'id', 'referrer', 'referrer_name',
            'candidate', 'candidate_name',
            'position', 'position_title',
            'referral_type', 'referral_type_display',
            'detected_type', 'detection_detail',
            'status', 'status_display',
            'bonus_amount', 'bonus_paid_at',
            'note', 'created_at',
        ]


class ReferralDetailSerializer(ReferralListSerializer):
    class Meta(ReferralListSerializer.Meta):
        fields = ReferralListSerializer.Meta.fields + ['updated_at']


class ReferralCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = [
            'referrer', 'candidate', 'position',
            'referral_type', 'note',
        ]
