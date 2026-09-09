"""品牌信息管理 (G43) 序列化器。"""
from rest_framework import serializers

from .models import BrandInfo


class BrandInfoSerializer(serializers.ModelSerializer):
    """雇主品牌信息序列化器。

    ``social_links`` 直接以 JSON 数组存取, 由前端保证结构
    (``[{ platform, label, url }]``); 后端只做基础非空校验。
    """

    class Meta:
        model = BrandInfo
        fields = [
            'id', 'company_name', 'brand_slogan', 'brand_intro',
            'logo_url', 'portal_title', 'portal_subtitle', 'portal_banner_url',
            'primary_color', 'contact_email', 'contact_phone', 'social_links',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_social_links(self, value):
        """social_links 必须是 list, 且每个元素是含 platform/label/url 的 dict。"""
        if not isinstance(value, list):
            raise serializers.ValidationError('social_links 必须是数组')
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError('social_links 每个元素必须是对象')
            if not item.get('url'):
                raise serializers.ValidationError('social_links 每项必须包含 url')
        return value
