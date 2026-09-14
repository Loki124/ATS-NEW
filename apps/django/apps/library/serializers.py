from rest_framework import serializers
from .models import School, Company, Major

# 注: 全局 camelCase 由 djangorestframework-camel-case 自动转换,
# 序列化器一律写 snake_case, 禁止手写 camelCase + source 映射。


class MajorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Major
        fields = [
            'id', 'spec_id', 'code', 'name',
            'education_level', 'education_level_code',
            'discipline', 'discipline_code',
            'category', 'category_code',
            'data_year', 'intro', 'detail_url',
        ]


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            'id', 'name', 'code', 'location', 'province', 'city',
            'education_level', 'school_type', 'school_category',
            'affiliated_to', 'tags', 'former_names', 'status',
        ]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'code', 'industry', 'scale', 'isBenchmark' if False else 'is_benchmark',
                  'description', 'status']
