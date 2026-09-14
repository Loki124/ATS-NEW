"""注册审核相关序列化器."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import RegistrationApplication

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """自助注册请求校验."""
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128)
    full_name = serializers.CharField(max_length=64, required=False, default='')

    def validate_email(self, value: str):
        value = value.strip().lower()
        if User.objects.filter(email=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError('该邮箱已被注册')
        if RegistrationApplication.objects.filter(email=value, status__in=['PENDING', 'APPROVED']).exists():
            raise serializers.ValidationError('该邮箱已有待审或已通过的注册申请')
        return value

    def validate_password(self, value: str):
        # 简单强度校验: 至少 8 位, 含字母与数字 (与后台改密策略对齐)
        if len(value) < 8:
            raise serializers.ValidationError('密码至少 8 位')
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise serializers.ValidationError('密码需同时包含字母和数字')
        return value


class VerifyRegisterCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)


class ResendRegisterCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class RegistrationApplicationSerializer(serializers.ModelSerializer):
    """注册申请列表/详情 (只读)."""
    username = serializers.CharField(source='user.username', read_only=True)
    email_verified = serializers.BooleanField(read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)

    class Meta:
        model = RegistrationApplication
        fields = (
            'id', 'username', 'email', 'full_name', 'status',
            'email_verified', 'created_at', 'reviewed_at',
            'reviewed_by_name', 'reject_reason',
        )
        read_only_fields = fields


class RegistrationReviewSerializer(serializers.Serializer):
    """审核通过/拒绝请求."""
    reject_reason = serializers.CharField(max_length=500, required=False, default='')
