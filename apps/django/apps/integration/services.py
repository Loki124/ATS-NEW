"""Integration Services (PRD v4 §14.4)

外部系统集成：
- MOKA (摩卡 HRIS) 同步
- 邮件服务（SMTP / SendGrid / 阿里云邮件）
- 企微机器人 / 应用消息
- 短信服务（阿里云 / 腾讯云）
- 背调服务
- 招聘门户

提供统一的发送接口，业务模块通过 integration.services 调用。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import smtplib
import time
import uuid
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import requests
from django.utils import timezone

from apps.common.exceptions import NotFound
from .crypto import SENSITIVE_KEYS, decrypt_secret_dict
from .models import IntegrationConfig, IntegrationSyncLog, IntegrationType

logger = logging.getLogger(__name__)


def _get_decrypted_config(integration_type: str) -> tuple[IntegrationConfig | None, dict]:
    """读取 IntegrationConfig 并合并解密敏感字段.

    返回 (config_obj, merged_dict).
    merged_dict 是 config(JSON) + decrypted_secret 合并, 业务代码可直接 cfg.get('corp_secret') 拿明文.
    """
    config = IntegrationConfig.objects.filter(
        type=integration_type, is_active=True,
    ).first()
    if not config:
        return None, {}
    cfg = dict(config.config or {})
    secret_raw = config.encrypted_secret or ''
    if secret_raw:
        try:
            secret_dict = json.loads(decrypt_secret(secret_raw))
        except Exception:
            logger.exception('IntegrationConfig %s: decrypt failed', integration_type)
            secret_dict = {}
        cfg.update(secret_dict)
    return config, cfg


def decrypt_secret(ciphertext: str) -> str:
    """local import 避免循环依赖"""
    from .crypto import decrypt_secret as _decrypt
    return _decrypt(ciphertext)


# ============================================================
# 邮件
# ============================================================
def send_email(to: str, subject: str, body: str, html: bool = False) -> bool:
    """发送邮件"""
    try:
        config, cfg = _get_decrypted_config(IntegrationType.EMAIL)
        if not config:
            logger.warning('Email integration not configured')
            return False
        smtp_host = cfg.get('smtp_host')
        smtp_port = cfg.get('smtp_port', 587)
        username = cfg.get('username')
        password = cfg.get('password')
        from_addr = cfg.get('from_address', username)
        use_tls = cfg.get('use_tls', True)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = to
        msg.attach(MIMEText(body, 'html' if html else 'plain', 'utf-8'))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.sendmail(from_addr, [to], msg.as_string())

        IntegrationSyncLog.objects.create(
            config=config,
            sync_type='SEND_EMAIL',
            status='SUCCESS',
            total_count=1,
            success_count=1,
            failed_count=0,
        )
        return True
    except Exception as e:
        logger.exception('Email send failed')
        try:
            IntegrationSyncLog.objects.create(
                config=config,
                sync_type='SEND_EMAIL',
                status='FAILED',
                total_count=1,
                success_count=0,
                failed_count=1,
                error_message=str(e),
            )
        except Exception:
            pass
        return False


# ============================================================
# 短信
# ============================================================
def send_sms(phone: str, content: str, template_id: Optional[str] = None,
             template_params: Optional[Dict[str, Any]] = None) -> bool:
    """发送短信"""
    try:
        config, cfg = _get_decrypted_config(IntegrationType.SMS)
        if not config:
            logger.warning('SMS integration not configured')
            return False
        provider = cfg.get('provider', 'aliyun')
        if provider == 'aliyun':
            return _send_sms_aliyun(cfg, phone, content, template_id, template_params)
        elif provider == 'tencent':
            return _send_sms_tencent(cfg, phone, content, template_id, template_params)
        else:
            logger.warning('Unknown SMS provider: %s', provider)
            return False
    except Exception as e:
        logger.exception('SMS send failed')
        return False


def _send_sms_aliyun(cfg, phone, content, template_id, template_params) -> bool:
    """阿里云短信"""
    try:
        import base64
        import hashlib
        import hmac
        import time
        import uuid
        access_key_id = cfg.get('access_key_id')
        access_key_secret = cfg.get('access_key_secret')
        sign_name = cfg.get('sign_name')
        endpoint = cfg.get('endpoint', 'https://dysmsapi.aliyuncs.com/')

        params = {
            'PhoneNumbers': phone,
            'SignName': sign_name,
            'TemplateCode': template_id or cfg.get('default_template'),
            'TemplateParam': json.dumps(template_params or {}),
            'AccessKeyId': access_key_id,
            'Timestamp': timezone.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'Format': 'JSON',
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureNonce': str(uuid.uuid4()),
            'SignatureVersion': '1.0',
            'RegionId': 'cn-hangzhou',
            'Action': 'SendSms',
            'Version': '2017-05-25',
        }
        # 签名（略过复杂实现）
        sorted_params = sorted(params.items())
        canonical = '&'.join(f'{requests.utils.quote(k, safe="")}={requests.utils.quote(v, safe="")}' for k, v in sorted_params)
        string_to_sign = f'GET&{requests.utils.quote("/", safe="")}&{requests.utils.quote(canonical, safe="")}'
        signature = base64.b64encode(
            hmac.new(
                f'{access_key_secret}&'.encode(), string_to_sign.encode(), hashlib.sha1,
            ).digest()
        ).decode()
        params['Signature'] = signature
        r = requests.get(endpoint, params=params, timeout=10)
        result = r.json()
        return result.get('Code') == 'OK'
    except Exception as e:
        logger.exception('Aliyun SMS failed: %s', e)
        return False


def _send_sms_tencent(cfg, phone, content, template_id, template_params) -> bool:
    """腾讯云短信（占位）"""
    logger.warning('Tencent SMS not implemented')
    return False


# ============================================================
# 企微
# ============================================================
def send_wecom_message(user_id: str, content: str, title: str = '') -> bool:
    """发送企微应用消息"""
    try:
        config, cfg = _get_decrypted_config(IntegrationType.WECOM)
        if not config:
            logger.warning('WeCom integration not configured')
            return False
        corp_id = cfg.get('corp_id')
        agent_id = cfg.get('agent_id')
        corp_secret = cfg.get('corp_secret')

        # 1. 获取 access_token
        token_url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
        r = requests.get(token_url, params={'corpid': corp_id, 'corpsecret': corp_secret}, timeout=10)
        access_token = r.json().get('access_token')
        if not access_token:
            logger.error('Wecom gettoken failed: %s', r.json())
            return False

        # 2. 发送应用消息
        send_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
        payload = {
            'touser': user_id,
            'msgtype': 'text',
            'agentid': agent_id,
            'text': {'content': f'{title}\n{content}' if title else content},
        }
        r = requests.post(send_url, json=payload, timeout=10)
        result = r.json()
        return result.get('errcode') == 0
    except Exception as e:
        logger.exception('Wecom message send failed: %s', e)
        return False


def send_wecom_robot(webhook_url: str, content: str, mentioned: Optional[List[str]] = None) -> bool:
    """发送企微群机器人消息"""
    try:
        payload = {
            'msgtype': 'text',
            'text': {'content': content, 'mentioned_list': mentioned or []},
        }
        r = requests.post(webhook_url, json=payload, timeout=10)
        return r.json().get('errcode') == 0
    except Exception as e:
        logger.exception('Wecom robot send failed: %s', e)
        return False


# ============================================================
# 摩卡同步
# ============================================================
def sync_candidate_from_moka(moka_id: str) -> Dict[str, Any]:
    """从摩卡拉取候选人"""
    try:
        config = IntegrationConfig.objects.filter(
            type=IntegrationType.MOKA, is_active=True,
        ).first()
        if not config:
            return {'success': False, 'error': 'Moka integration not configured'}
        cfg = config.config or {}
        base_url = cfg.get('base_url')
        api_key = cfg.get('api_key')
        headers = {'Authorization': f'Bearer {api_key}'}
        r = requests.get(f'{base_url}/candidates/{moka_id}', headers=headers, timeout=10)
        if r.status_code == 200:
            return {'success': True, 'data': r.json()}
        return {'success': False, 'error': f'HTTP {r.status_code}'}
    except Exception as e:
        logger.exception('Moka sync failed: %s', e)
        return {'success': False, 'error': str(e)}


def push_candidate_to_moka(candidate_data: Dict[str, Any]) -> Dict[str, Any]:
    """推送候选人至摩卡"""
    try:
        config = IntegrationConfig.objects.filter(
            type=IntegrationType.MOKA, is_active=True,
        ).first()
        if not config:
            return {'success': False, 'error': 'Moka integration not configured'}
        cfg = config.config or {}
        base_url = cfg.get('base_url')
        api_key = cfg.get('api_key')
        headers = {'Authorization': f'Bearer {api_key}'}
        r = requests.post(f'{base_url}/candidates', json=candidate_data, headers=headers, timeout=10)
        if r.status_code in (200, 201):
            return {'success': True, 'data': r.json()}
        return {'success': False, 'error': f'HTTP {r.status_code}: {r.text}'}
    except Exception as e:
        logger.exception('Moka push failed: %s', e)
        return {'success': False, 'error': str(e)}


# ============================================================
# 背调（统一规范 v1.0.1：HMAC-SHA256 双向签名 + 调用审计）
# ============================================================
def _bg_sign(app_id: str, app_key: str, params: dict) -> tuple[str, str]:
    """规范 §1.4.3 签名：待签串 = 排序业务参数(key=value&) + '&timestamp=' + ts。"""
    ts = str(int(time.time() * 1000))
    biz = {k: v for k, v in (params or {}).items() if v is not None and v != ''}
    raw = '&'.join(f'{k}={v}' for k, v in sorted(biz.items()))
    sign_str = f'{raw}&timestamp={ts}' if raw else f'timestamp={ts}'
    sign = hmac.new(app_key.encode('utf-8'), sign_str.encode('utf-8'), hashlib.sha256).hexdigest()
    return ts, sign


def _bg_headers(app_id: str, app_key: str, params: dict) -> dict:
    ts, sign = _bg_sign(app_id, app_key, params)
    return {
        'X-App-Id': app_id,
        'X-Timestamp': ts,
        'X-App-Sign': sign,
        'Content-Type': 'application/json',
    }


def _bg_secret(config: IntegrationConfig) -> dict:
    secret_raw = config.encrypted_secret or ''
    if not secret_raw:
        return {}
    try:
        return json.loads(decrypt_secret(secret_raw))
    except Exception:
        logger.warning('IntegrationConfig %s: decrypt secret failed', config.id)
        return {}


def test_background_check_connection(config: IntegrationConfig) -> Dict[str, Any]:
    """测试连接：按规范 HMAC 向供应商发真实签名请求（套餐查询），校验连通性与凭证。"""
    try:
        cfg = config.config or {}
        secret = _bg_secret(config)
        app_id = cfg.get('AppId', cfg.get('appId', ''))
        app_key = secret.get('api_key') or secret.get('appKey') or ''
        if not app_id or not app_key:
            return {'success': False, 'message': '缺少 appId / appKey 配置'}
        env = cfg.get('env', 'sandbox')
        base_url = cfg.get('productionBaseUrl') if env == 'production' else cfg.get('sandboxBaseUrl')
        if not base_url:
            return {'success': False, 'message': '未配置 BaseURL'}
        path = cfg.get('productsPath') or '/api/v1/background-check/products'
        url = f'{base_url.rstrip("/")}{path}'
        headers = _bg_headers(app_id, app_key, {})
        t0 = time.time()
        try:
            r = requests.get(url, headers=headers, timeout=10)
            duration_ms = int((time.time() - t0) * 1000)
            detail = ''
            try:
                resp = r.json()
                detail = f"code={resp.get('code')}, message={resp.get('message')}"
                ok = r.status_code == 200 and resp.get('code') in (0, '0', None)
            except Exception:
                ok = r.status_code == 200
                detail = r.text[:200]
            IntegrationSyncLog.objects.create(
                config=config, sync_type='TEST_CONNECTION',
                status='SUCCESS' if ok else 'FAILED',
                endpoint=path, method='GET', direction='OUT', duration_ms=duration_ms,
                error_message='' if ok else f'HTTP {r.status_code}: {detail}',
            )
            return {'success': ok, 'message': '连接成功' if ok else f'连接失败: HTTP {r.status_code} {detail}', 'duration_ms': duration_ms}
        except requests.RequestException as e:
            duration_ms = int((time.time() - t0) * 1000)
            IntegrationSyncLog.objects.create(
                config=config, sync_type='TEST_CONNECTION', status='FAILED',
                endpoint=path, method='GET', direction='OUT', duration_ms=duration_ms,
                error_message=str(e),
            )
            return {'success': False, 'message': f'连接异常: {e}'}
    except Exception as e:
        logger.exception('test_background_check_connection failed')
        return {'success': False, 'message': f'测试失败: {e}'}


def request_background_check(candidate_id: str, items: List[str], config_id: str = None) -> Dict[str, Any]:
    """发起背调（统一规范 v1.0.1：HMAC 签名 + 调用审计）。"""
    try:
        qs = IntegrationConfig.objects.filter(type=IntegrationType.BACKGROUND_CHECK, is_active=True)
        if config_id:
            qs = IntegrationConfig.objects.filter(id=config_id, type=IntegrationType.BACKGROUND_CHECK)
        config = qs.first()
        if not config:
            return {'success': False, 'error': 'Background check not configured'}
        cfg = config.config or {}
        secret = _bg_secret(config)
        app_id = cfg.get('AppId', cfg.get('appId', ''))
        app_key = secret.get('api_key') or secret.get('appKey') or ''
        env = cfg.get('env', 'sandbox')
        base_url = cfg.get('productionBaseUrl') if env == 'production' else cfg.get('sandboxBaseUrl')
        path = cfg.get('createPath') or '/api/v1/background-check/orders'
        url = f'{base_url.rstrip("/")}{path}'
        params = {
            'requestId': str(uuid.uuid4()),
            'candidateId': candidate_id,
            'items': items,
        }
        headers = _bg_headers(app_id, app_key, params)
        t0 = time.time()
        r = requests.post(url, json=params, headers=headers, timeout=10)
        duration_ms = int((time.time() - t0) * 1000)
        try:
            resp = r.json()
        except Exception:
            resp = {}
        ok = r.status_code in (200, 201)
        IntegrationSyncLog.objects.create(
            config=config, sync_type='CREATE_ORDER',
            status='SUCCESS' if ok else 'FAILED',
            endpoint=path, method='POST', direction='OUT', duration_ms=duration_ms,
            error_message='' if ok else f'HTTP {r.status_code}: {r.text[:200]}',
        )
        if ok:
            return {'success': True, 'data': resp}
        return {'success': False, 'error': f'HTTP {r.status_code}: {resp.get("message", "")}'}
    except Exception as e:
        logger.exception('Background check request failed: %s', e)
        return {'success': False, 'error': str(e)}


# ============================================================
# 招聘门户
# ============================================================
def sync_position_to_portal(position_id: str) -> Dict[str, Any]:
    """同步职位到外部招聘门户"""
    try:
        config = IntegrationConfig.objects.filter(
            type=IntegrationType.PORTAL, is_active=True,
        ).first()
        if not config:
            return {'success': False, 'error': 'Portal integration not configured'}
        cfg = config.config or {}
        base_url = cfg.get('base_url')
        api_key = cfg.get('api_key')
        r = requests.post(
            f'{base_url}/positions',
            json={'position_id': position_id},
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=10,
        )
        if r.status_code in (200, 201):
            return {'success': True, 'data': r.json()}
        return {'success': False, 'error': f'HTTP {r.status_code}'}
    except Exception as e:
        logger.exception('Portal sync failed: %s', e)
        return {'success': False, 'error': str(e)}
