from rest_framework import serializers

from .models import Company, Major, School

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
            'updated_at', 'is_customized',
        ]
        read_only_fields = ['spec_id', 'updated_at']
        # id 由模型 save() 自动生成 nanoid，不是前端传的；不设为 read_only 会导致
        # POST 报「id: 该字段是必填项」
        extra_kwargs = {'id': {'read_only': True}}


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            'id', 'name', 'code', 'location', 'province', 'city',
            'education_level', 'school_type', 'school_category',
            'affiliated_to', 'tags', 'former_names', 'status',
            'updated_at', 'is_customized',
        ]
        read_only_fields = ['updated_at']
        # 同上：id 由模型 save() 自动生成 nanoid，必须 read_only，否则 POST 必填报错
        extra_kwargs = {'id': {'read_only': True}}


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'code', 'industry', 'scale', 'isBenchmark' if False else 'is_benchmark',
                  'description', 'status']
