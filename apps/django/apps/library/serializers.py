from rest_framework import serializers
from .models import School, Company


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
