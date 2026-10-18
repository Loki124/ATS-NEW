"""邮箱验证码登录相关序列化器."""
from rest_framework import serializers


class SendLoginCodeSerializer(serializers.Serializer):
    """发送邮箱登录验证码请求."""
    email = serializers.EmailField()


class EmailLoginSerializer(serializers.Serializer):
    """邮箱验证码登录请求（免密）."""
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
