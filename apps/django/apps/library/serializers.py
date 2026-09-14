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
        fields = ['id', 'name', 'code', 'location', 'province', 'city',
                  'educationLevel' if False else 'education_level',
                  'schoolType' if False else 'school_type',
                  'schoolCategory' if False else 'school_category',
                  'status']
        # 注: FE 接口需要 camelCase, 但 stub 直接返 snake_case 也可 (DRF ContentNegotiation)
        # 真正做 G41 任务时再统一桥接


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'code', 'industry', 'scale', 'isBenchmark' if False else 'is_benchmark',
                  'description', 'status']
