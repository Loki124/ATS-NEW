"""标准简历 / 申请表(多表单) 序列化器

约定（与全项目一致）：序列器统一用 snake_case 字段名，
camelCase ↔ snake_case 的双向转换由 djangorestframework-camel-case 负责：
- 入站 CamelCaseJSONParser：前端 camelCase JSON → 序列器看到 snake_case
- 出站 CamelCaseJSONRenderer：snake_case → 前端 camelCase JSON

因此此处严禁再写 source='form_type' 之类的手动 camelCase↔snake_case 映射，
否则会与该包的自动转换叠加，导致前端 camelCase 字段进来后被转成 snake_case、
序列器却按 camelCase 字段名查找而报「必填」(本项目 application-form 400 即此坑)。
"""
from rest_framework import serializers

from .models import RegistrationForm


class RegistrationFormSerializer(serializers.ModelSerializer):
    """登记 / 申请表（多套）序列化器"""

    class Meta:
        model = RegistrationForm
        fields = [
            'id', 'name', 'form_type', 'departments', 'mode',
            'fields', 'order_index', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
