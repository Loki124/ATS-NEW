"""码表库 (G46) 序列化器。

⚠️ 项目全局启用 djangorestframework-camel-case，序列化器一律使用 snake_case 字段名，
禁止手写 camelCase + source 映射（会与自动转换叠加导致入站字段对不上）。
"""
from rest_framework import serializers
from django.db.models import Q

from .models import Country, Ethnicity, Language, Region, BusinessCode


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['code', 'name', 'level', 'parent_code']


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['code', 'code3', 'name_cn', 'name_en', 'phone_code']


class EthnicitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ethnicity
        fields = ['code', 'name', 'letter_code']


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['code', 'name_cn', 'name_en']


class BusinessCodeSerializer(serializers.ModelSerializer):
    """业务码表（自定义枚举）序列化器。

    唯一性：(category, code) 同类下唯一。因模型用软删（无 DB 唯一约束，否则删除后再建同
    code 会撞键），唯一性在应用层校验——仅比对未软删行，更新时排除自身。
    """

    class Meta:
        model = BusinessCode
        fields = [
            'id', 'category', 'code', 'name', 'description',
            'parent_code', 'sort_order', 'is_customized', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']

    def validate(self, attrs):
        category = attrs.get('category') or getattr(self.instance, 'category', None)
        code = (attrs.get('code') or '').strip() or getattr(self.instance, 'code', None)
        if category and code:
            qs = BusinessCode.objects.filter(
                category=category, code=code, deleted_at__isnull=True,
            )
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'code': ['同一类别下编码「%s」已存在' % code]}
                )
        return attrs
