from rest_framework import serializers

from .models import DynamicField


class DynamicFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicField
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
