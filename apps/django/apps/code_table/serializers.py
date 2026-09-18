"""码表库 (G46) 序列化器。

⚠️ 项目全局启用 djangorestframework-camel-case，序列化器一律使用 snake_case 字段名，
禁止手写 camelCase + source 映射（会与自动转换叠加导致入站字段对不上）。
"""
from rest_framework import serializers

from .models import Country, Currency, Ethnicity, Industry, Language, Region


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


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['code', 'code_numeric', 'symbol', 'name_cn', 'name_en']


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ['code', 'name', 'level', 'parent_code']
