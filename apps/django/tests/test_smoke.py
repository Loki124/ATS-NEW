"""测试配置检查 - 验证项目能正常启动测试"""
import pytest
from django.conf import settings
from django.urls import reverse


def test_django_settings_loaded():
    assert settings.DATABASES['default']['ENGINE']


def test_authenticated_request_returns_200(auth_client):
    """验证认证 client 正常工作"""
    response = auth_client.get('/api/v1/auth/me/')
    assert response.status_code == 200


def test_unauthenticated_request_returns_401(api_client):
    """未认证请求应返回 401"""
    response = api_client.get('/api/v1/candidates/')
    assert response.status_code == 401


def test_health_check(api_client):
    response = api_client.get('/health/')
    assert response.status_code in (200, 503)
