"""背调测试 fixtures。"""
import json

import pytest

from apps.integration.crypto import encrypt_secret
from apps.integration.models import IntegrationConfig


@pytest.fixture
def bg_config(db):
    """一个启用中的 HMAC 背调供应商配置；appId=sp_test, api_key=testkey。"""
    cfg = {
        'env': 'sandbox',
        'sandboxBaseUrl': 'https://sandbox.example.test',
        'AppId': 'sp_test',
        'provider': '',
    }
    return IntegrationConfig.objects.create(
        type='BACKGROUND_CHECK',
        name='Test BG',
        provider='',
        config=cfg,
        encrypted_secret=encrypt_secret(json.dumps({'api_key': 'testkey'})),
        is_active=True,
    )
