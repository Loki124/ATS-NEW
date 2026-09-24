"""校招专属序列化器。"""
from rest_framework import serializers

from .models import CampusAmbassador, CampusSession


class CampusAmbassadorSerializer(serializers.ModelSerializer):
    """校园大使序列化器。recruit_type 由后端写入（读侧隔离 + 写侧守卫），前端只读。"""

    class Meta:
        model = CampusAmbassador
        fields = [
            'id', 'school', 'name', 'region', 'status', 'phone', 'note',
            'recruit_type', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'recruit_type', 'created_at', 'updated_at']


class CampusSessionSerializer(serializers.ModelSerializer):
    """宣讲会序列化器。recruit_type 由后端写入，前端只读。"""

    class Meta:
        model = CampusSession
        fields = [
            'id', 'title', 'school', 'session_type', 'start_time', 'end_time',
            'venue', 'online_link', 'capacity', 'status', 'note',
            'recruit_type', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'recruit_type', 'created_at', 'updated_at']
