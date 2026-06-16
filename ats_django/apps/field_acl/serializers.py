"""Field ACL Serializers (PRD v4 §4.4)"""
from rest_framework import serializers

from .models import FieldACL


class FieldACLSerializer(serializers.ModelSerializer):
    permission_display = serializers.CharField(source='get_permission_display', read_only=True)

    class Meta:
        model = FieldACL
        fields = [
            'id', 'entity', 'field', 'role_code',
            'permission', 'permission_display',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
