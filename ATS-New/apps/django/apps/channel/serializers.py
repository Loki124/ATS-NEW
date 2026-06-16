"""Channel Serializers (PRD v4 §14.5 渠道)"""
from rest_framework import serializers

from .models import Channel, ChannelCost


class ChannelSerializer(serializers.ModelSerializer):
    cost_count = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = [
            'id', 'name', 'code', 'category',
            'cost_per_resume', 'cost_per_hire', 'total_cost',
            'contact_name', 'contact_phone', 'is_active',
            'cost_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total_cost', 'created_at', 'updated_at']

    def get_cost_count(self, obj) -> int:
        return obj.costs.filter(deleted_at__isnull=True).count() if hasattr(obj, 'costs') else 0


class ChannelCostSerializer(serializers.ModelSerializer):
    channel_name = serializers.CharField(source='channel.name', read_only=True, default='')

    class Meta:
        model = ChannelCost
        fields = [
            'id', 'channel', 'channel_name',
            'amount', 'cost_type', 'description', 'incurred_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
