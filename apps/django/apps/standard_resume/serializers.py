"""标准简历 / 申请表(多表单) 序列化器

字段输出 camelCase（与项目前端约定一致：createdAt / formType / isActive / orderIndex），
写入时 DRF 通过 source 映射自动反解到 model 的 snake_case 字段。
"""
from rest_framework import serializers

from .models import RegistrationForm


class RegistrationFormSerializer(serializers.ModelSerializer):
    """登记 / 申请表（多套）序列化器"""

    formType = serializers.ChoiceField(
        source='form_type', choices=RegistrationForm.FORM_TYPE_CHOICES,
    )
    isActive = serializers.BooleanField(source='is_active')
    orderIndex = serializers.IntegerField(source='order_index')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = RegistrationForm
        fields = [
            'id', 'name', 'formType', 'departments', 'mode',
            'fields', 'orderIndex', 'isActive',
            'createdAt', 'updatedAt',
        ]
        read_only_fields = ['id', 'createdAt', 'updatedAt']
