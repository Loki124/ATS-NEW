"""P1-2 第二批范式回归: 验证 integration/services.py 改用窄集 except 后行为正确。

两份契约:
  1. 窄集异常 (网络 IO / ORM / 协议 / 解析) 仍被捕获, 调用方收到 False/失败 dict 而非 500;
  2. 编程错误 (AttributeError / NameError / TypeError 等) 不再被静默吞, 应向外抛。

测试策略: 用 unittest.mock 替换 requests.post / requests.get, 让其抛目标异常。

T19 (P1-2 第二批): integration 模块, 真正的"高价值高风险" 目标 (第三方 IO + 背调回调).
"""
from __future__ import annotations

import json
import smtplib
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.db import OperationalError

from apps.integration.services import (
    send_email,
    send_sms,
    send_wecom_message,
    send_wecom_robot,
    sync_candidate_from_moka,
    push_candidate_to_moka,
    sync_position_to_portal,
)


# ============================================================
# 通用 helpers
# ============================================================

class _Resp:
    """最小 requests.Response 桩 (与 test_hmac_network 同形)."""

    def __init__(self, status_code=200, json_data=None, content=b'', headers=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.content = content
        self.headers = headers or {'Content-Type': 'application/json'}

    def json(self):
        return self._json


# ============================================================
# send_email (SMTP)
# ============================================================

@patch('apps.integration.services.IntegrationSyncLog')
@patch('apps.integration.services.smtplib.SMTP')
@patch('apps.integration.services._get_decrypted_config')
def test_send_email_smtp_exception_swallowed(mock_get_cfg, mock_smtp_cls, mock_sync_log):
    """SMTPException 仍被吞 → 返 False, 不外抛。"""
    cfg = MagicMock(spec=['id', 'config'])  # 不暴露为 IntegrationConfig 实例, 仅 id 属性
    cfg.id = 'cfg-1'
    mock_get_cfg.return_value = (cfg, {
        'smtp_host': 'smtp.test.com', 'smtp_port': 587,
        'username': 'u', 'password': 'p', 'from_address': 'a@b.com',
        'use_tls': True,
    })
    mock_smtp_cls.side_effect = smtplib.SMTPException('mocked smtp conn refused')

    ok = send_email('to@b.com', 'subj', 'body')
    assert ok is False


@patch('apps.integration.services.IntegrationSyncLog')
@patch('apps.integration.services._get_decrypted_config')
def test_send_email_attribute_error_no_longer_swallowed(mock_get_cfg, mock_sync_log):
    """_get_decrypted_config 触发 AttributeError 不再被吞 → 向上抛。"""
    mock_get_cfg.side_effect = AttributeError('mocked typo in cfg resolution')

    with pytest.raises(AttributeError, match='mocked typo'):
        send_email('to@b.com', 'subj', 'body')


# ============================================================
# send_sms / _send_sms_aliyun (HTTP SDK)
# ============================================================

@patch('apps.integration.services.requests.get')
@patch('apps.integration.services._get_decrypted_config')
def test_send_sms_connection_error_swallowed(mock_get_cfg, mock_get):
    """ConnectionError 仍被吞 → 返 False。"""
    mock_get_cfg.return_value = (None, {})  # 未配置 → 早退; 改测已配置路径
    # 改用已配置
    cfg = MagicMock()
    cfg.id = 'cfg-2'
    mock_get_cfg.return_value = (cfg, {'provider': 'aliyun'})

    # 直接测 _send_sms_aliyun: 让 requests.get 抛 ConnectionError
    from apps.integration.services import _send_sms_aliyun
    mock_get.side_effect = requests.ConnectionError('mocked conn refused')

    ok = _send_sms_aliyun(
        cfg={'access_key_id': 'k', 'access_key_secret': 's', 'sign_name': 'S',
             'template_id': 'T', 'endpoint': 'https://x'},
        phone='13800000000', content='hi', template_id='T', template_params=None,
    )
    assert ok is False


@patch('apps.integration.services.requests.get')
@patch('apps.integration.services._get_decrypted_config')
def test_send_sms_attribute_error_no_longer_swallowed(mock_get_cfg, mock_get):
    """Aliyun 签名阶段 AttributeError 不再被吞。

    模拟 requests.get 返回 json() 抛 AttributeError 的响应,
    让 except (ConnectionError, ...) 不捕获, 应向上抛。
    """
    from apps.integration.services import _send_sms_aliyun

    bad = MagicMock()
    bad.status_code = 200
    bad.json.side_effect = AttributeError('mocked typo')
    mock_get.return_value = bad

    with pytest.raises(AttributeError, match='mocked typo'):
        _send_sms_aliyun(
            cfg={'access_key_id': 'k', 'access_key_secret': 's', 'sign_name': 'S',
                 'template_id': 'T', 'endpoint': 'https://x'},
            phone='13800000000', content='hi', template_id='T', template_params=None,
        )


# ============================================================
# send_wecom_message / send_wecom_robot (HTTP API)
# ============================================================

@patch('apps.integration.services.requests.post')
@patch('apps.integration.services.requests.get')
@patch('apps.integration.services._get_decrypted_config')
def test_send_wecom_message_connection_error_swallowed(mock_get_cfg, mock_get, mock_post):
    """ConnectionError 仍被吞 → 返 False。"""
    cfg = MagicMock()
    mock_get_cfg.return_value = (cfg, {
        'corp_id': 'cid', 'agent_id': 1, 'corp_secret': 'sec',
    })
    # 1) token 获取 OK
    ok_resp = _Resp(200, {'access_token': 'tk', 'errcode': 0})
    mock_get.return_value = ok_resp
    # 2) 发送阶段抛 ConnectionError
    mock_post.side_effect = requests.ConnectionError('mocked conn refused')

    ok = send_wecom_message(user_id='u', content='hi')
    assert ok is False


@patch('apps.integration.services.requests.post')
@patch('apps.integration.services.requests.get')
@patch('apps.integration.services._get_decrypted_config')
def test_send_wecom_message_attribute_error_no_longer_swallowed(mock_get_cfg, mock_get, mock_post):
    """请求体构造后 send_url 阶段 json() 抛 AttributeError 不再被吞, 应向上抛。

    get token OK, post 抛 AttributeError (模拟下游 SDK/代码缺陷).
    """
    cfg = MagicMock()
    mock_get_cfg.return_value = (cfg, {
        'corp_id': 'cid', 'agent_id': 1, 'corp_secret': 'sec',
    })
    ok_resp = _Resp(200, {'access_token': 'tk', 'errcode': 0})
    mock_get.return_value = ok_resp

    mock_post.side_effect = AttributeError('mocked typo')

    with pytest.raises(AttributeError, match='mocked typo'):
        send_wecom_message(user_id='u', content='hi')


@patch('apps.integration.services.requests.post')
def test_send_wecom_robot_connection_error_swallowed(mock_post):
    mock_post.side_effect = requests.ConnectionError('mocked conn refused')
    ok = send_wecom_robot(webhook_url='https://x', content='hi')
    assert ok is False


@patch('apps.integration.services.requests.post')
def test_send_wecom_robot_attribute_error_no_longer_swallowed(mock_post):
    """访问 webhook URL 拼接阶段 AttributeError 不再被吞。

    模拟 requests.post 返回一个 json() 抛 AttributeError 的响应.
    """
    bad = MagicMock()
    bad.status_code = 200
    bad.json.side_effect = AttributeError('mocked typo')
    mock_post.return_value = bad

    with pytest.raises(AttributeError, match='mocked typo'):
        send_wecom_robot(webhook_url='https://x', content='hi')


# ============================================================
# Moka sync / push (HTTP GET/POST)
# ============================================================

@patch('apps.integration.services.IntegrationConfig')
@patch('apps.integration.services.requests.get')
def test_sync_candidate_from_moka_connection_error_swallowed(mock_get, mock_model):
    cfg = MagicMock(); cfg.id = 'cfg-moka'; cfg.config = {'base_url': 'https://m', 'api_key': 'k'}
    mock_model.objects.filter.return_value.first.return_value = cfg
    mock_get.side_effect = requests.ConnectionError('mocked conn refused')

    res = sync_candidate_from_moka('C1')
    assert res['success'] is False
    assert 'mocked conn refused' in res['error']


@patch('apps.integration.services.requests.get')
def test_sync_candidate_from_moka_attribute_error_no_longer_swallowed(mock_get):
    """base_url 拼接阶段 AttributeError 不再被吞。

    模拟 requests.get 返回一个 status_code=200 但 json() 抛 AttributeError 的响应,
    让 except (ConnectionError, ...) 不捕获, 应向上抛。
    """
    bad = MagicMock()
    bad.status_code = 200
    bad.json.side_effect = AttributeError('mocked typo')
    mock_get.return_value = bad

    cfg = MagicMock(); cfg.id = 'cfg-moka'; cfg.config = {'base_url': 'https://m', 'api_key': 'k'}
    with patch('apps.integration.services.IntegrationConfig') as MockCfg:
        MockCfg.objects.filter.return_value.first.return_value = cfg
        with pytest.raises(AttributeError, match='mocked typo'):
            sync_candidate_from_moka('C1')


@patch('apps.integration.services.IntegrationConfig')
@patch('apps.integration.services.requests.post')
def test_push_candidate_to_moka_timeout_swallowed(mock_post, mock_model):
    cfg = MagicMock(); cfg.id = 'cfg-moka'; cfg.config = {'base_url': 'https://m', 'api_key': 'k'}
    mock_model.objects.filter.return_value.first.return_value = cfg
    mock_post.side_effect = requests.Timeout('mocked timeout')

    res = push_candidate_to_moka({'candidate_id': 'C1'})
    assert res['success'] is False
    assert 'mocked timeout' in res['error']


# ============================================================
# sync_position_to_portal (HTTP POST)
# ============================================================

@patch('apps.integration.services.IntegrationConfig')
@patch('apps.integration.services.requests.post')
def test_sync_position_to_portal_value_error_swallowed(mock_post, mock_model):
    """r.json() 抛 ValueError (响应不是 JSON) 仍被吞 → 返 False dict。"""
    cfg = MagicMock(); cfg.id = 'cfg-portal'; cfg.config = {'base_url': 'https://p', 'api_key': 'k'}
    mock_model.objects.filter.return_value.first.return_value = cfg
    mock_post.return_value = _Resp(status_code=200)

    with patch.object(_Resp, 'json', side_effect=ValueError('mocked invalid json')):
        res = sync_position_to_portal('pos-1')
    assert res['success'] is False
    assert 'mocked invalid json' in res['error']


@patch('apps.integration.services.IntegrationConfig')
@patch('apps.integration.services.requests.post')
def test_sync_position_to_portal_attribute_error_no_longer_swallowed(mock_post, mock_model):
    cfg = MagicMock(); cfg.id = 'cfg-portal'; cfg.config = {'base_url': 'https://p', 'api_key': 'k'}
    mock_model.objects.filter.return_value.first.return_value = cfg
    mock_post.side_effect = AttributeError('mocked typo')

    with pytest.raises(AttributeError, match='mocked typo'):
        sync_position_to_portal('pos-1')