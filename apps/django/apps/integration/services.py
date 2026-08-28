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
from datetime import datetime as dt_datetime, timezone as dt_timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import requests
from django.utils import timezone

from apps.common.exceptions import NotFound
from .crypto import SENSITIVE_KEYS, decrypt_secret_dict
from .models import (
    IntegrationConfig,
    IntegrationSyncLog,
    IntegrationType,
    BackgroundCheckOrder,
    BackgroundCheckOrderEvent,
    BGOrderStatus,
    BGRiskLevel,
    ALLOWED_ORDER_TRANSITIONS,
)

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
            # 出向成功：落初始订单（状态机起点 status=0 已受理），关联候选人
            order_number = (resp.get('data') or {}).get('number')
            if order_number:
                try:
                    create_background_check_order(
                        config=config, candidate_id=str(candidate_id),
                        items=items, order_number=str(order_number), request_payload=params,
                    )
                except Exception:
                    logger.exception('create_background_check_order failed (number=%s)', order_number)
            return {'success': True, 'data': resp}
        return {'success': False, 'error': f'HTTP {r.status_code}: {resp.get("message", "")}'}
    except Exception as e:
        logger.exception('Background check request failed: %s', e)
        return {'success': False, 'error': str(e)}


def _ms_to_datetime(ms) -> Optional[dt_datetime]:
    """Unix 毫秒时间戳 -> 时区感知 datetime（UTC），非法值返回 None。"""
    if ms is None:
        return None
    try:
        return dt_datetime.fromtimestamp(int(ms) / 1000, tz=dt_timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def create_background_check_order(config: IntegrationConfig, candidate_id: str, items: List[str],
                                  order_number: str, candidate_name: str = '',
                                  request_payload: Optional[dict] = None) -> BackgroundCheckOrder:
    """落初始背调订单（状态机起点 status=0 已受理）。

    幂等：同一 (config, order_number) 已存在则直接返回，不重复写 CREATE 事件。
    返回 BackgroundCheckOrder。
    """
    order, created = BackgroundCheckOrder.objects.get_or_create(
        config=config, order_number=str(order_number),
        defaults={
            'candidate_id': str(candidate_id or ''),
            'candidate_name': candidate_name or '',
            'status': BGOrderStatus.ACCEPTED,
            'status_name': BGOrderStatus.ACCEPTED.label,
            'latest_payload': request_payload,
        },
    )
    if created:
        BackgroundCheckOrderEvent.objects.create(
            order=order, config=config, from_status=None, to_status=BGOrderStatus.ACCEPTED,
            source='CREATE', is_legal_transition=True, raw_payload=request_payload,
        )
    return order


def apply_callback_to_order(payload: dict, config: IntegrationConfig,
                            sync_log: Optional[IntegrationSyncLog] = None
                            ) -> tuple[BackgroundCheckOrder, Optional[BackgroundCheckOrderEvent], str]:
    """回调驱动订单状态机（规范 §5.3 幂等 + 状态机转移）。

    参数:
        payload: 已验签的回调体（number/status/statusName/riskLevel/reportUrl/completionTime）
        config: 命中的 IntegrationConfig
        sync_log: 关联的 IntegrationSyncLog（审计 SUCCESS 那条），可为空
    返回:
        (order, event, action) —— action ∈ {'created','updated','noop'}
        - created: 首次按 callback 状态建单（懒建，创建订单接口未先落库的场景）
        - updated: 状态发生变更，已写转移事件
        - noop: 状态与完成时间/风险一致，幂等不重复处理
    """
    number = str(payload.get('number', ''))
    status_val = payload.get('status')
    status_name = payload.get('statusName') or BGOrderStatus.label_of(status_val) or ''
    risk_level = payload.get('riskLevel')
    report_url = payload.get('reportUrl') or ''
    completion_time = _ms_to_datetime(payload.get('completionTime'))

    order, created = BackgroundCheckOrder.objects.get_or_create(
        config=config, order_number=number,
        defaults={
            'status': status_val, 'status_name': status_name,
            'risk_level': risk_level, 'report_url': report_url,
            'completion_time': completion_time, 'latest_payload': payload,
        },
    )
    if created:
        ev = BackgroundCheckOrderEvent.objects.create(
            order=order, config=config, from_status=None, to_status=status_val,
            risk_level=risk_level, report_url=report_url, completion_time=completion_time,
            source='CALLBACK', is_legal_transition=True, raw_payload=payload, sync_log=sync_log,
        )
        return order, ev, 'created'

    # 已存在：状态 + 完成时间 + 风险一致 → 幂等 noop（审计已记录 SUCCESS，不重复落事件）
    if (order.status == status_val
            and order.completion_time == completion_time
            and order.risk_level == risk_level):
        return order, None, 'noop'

    from_status = order.status
    is_legal = status_val in ALLOWED_ORDER_TRANSITIONS.get(from_status, set())
    if not is_legal:
        logger.warning('BG order %s 非合法转移 %s->%s（供应商权威，仍落库）',
                       number, from_status, status_val)
    ev = BackgroundCheckOrderEvent.objects.create(
        order=order, config=config, from_status=from_status, to_status=status_val,
        risk_level=risk_level, report_url=report_url, completion_time=completion_time,
        source='CALLBACK', is_legal_transition=is_legal, raw_payload=payload, sync_log=sync_log,
    )
    order.status = status_val
    order.status_name = status_name
    if risk_level is not None:
        order.risk_level = risk_level
    order.report_url = report_url
    if completion_time is not None:
        order.completion_time = completion_time
    order.latest_payload = payload
    order.save(update_fields=['status', 'status_name', 'risk_level',
                              'report_url', 'completion_time', 'latest_payload', 'updated_at'])
    return order, ev, 'updated'


def cancel_background_check_order(order: BackgroundCheckOrder,
                                  config: Optional[IntegrationConfig] = None) -> Dict[str, Any]:
    """平台发起取消（状态机置 6 已取消）。

    先按规范向供应商取消接口发签名出向（best-effort），再在平台侧置为已取消。
    平台发起的取消具有权威性，无论出向成败均落 CANCEL 事件。
    """
    config = config or order.config
    result: Dict[str, Any] = {'success': True, 'message': '已取消'}
    try:
        cfg = config.config or {}
        secret = _bg_secret(config)
        app_id = cfg.get('AppId', cfg.get('appId', ''))
        app_key = secret.get('api_key') or secret.get('apiKey') or ''
        env = cfg.get('env', 'sandbox')
        base_url = cfg.get('productionBaseUrl') if env == 'production' else cfg.get('sandboxBaseUrl')
        path = cfg.get('cancelPath') or '/api/v1/background-check/cancel'
        if base_url and app_key:
            url = f'{base_url.rstrip("/")}{path}'
            params = {'number': order.order_number}
            headers = _bg_headers(app_id, app_key, params)
            t0 = time.time()
            try:
                r = requests.post(url, json=params, headers=headers, timeout=10)
                duration_ms = int((time.time() - t0) * 1000)
                try:
                    resp = r.json()
                except Exception:
                    resp = {}
                ok = r.status_code in (200, 201) and resp.get('code') in (0, '0', None)
                IntegrationSyncLog.objects.create(
                    config=config, sync_type='CANCEL_ORDER',
                    status='SUCCESS' if ok else 'FAILED',
                    endpoint=path, method='POST', direction='OUT', duration_ms=duration_ms,
                    error_message='' if ok else f'HTTP {r.status_code}: {r.text[:200]}',
                )
                if not ok:
                    result = {'success': False,
                              'message': f'供应商取消失败: HTTP {r.status_code} {resp.get("message", "")}'}
            except requests.RequestException as e:
                IntegrationSyncLog.objects.create(
                    config=config, sync_type='CANCEL_ORDER', status='FAILED',
                    endpoint=path, method='POST', direction='OUT',
                    duration_ms=int((time.time() - t0) * 1000), error_message=str(e),
                )
                result = {'success': False, 'message': f'供应商取消异常: {e}'}

        # 平台侧置为已取消
        from_status = order.status
        if from_status != BGOrderStatus.CANCELLED:
            is_legal = BGOrderStatus.CANCELLED in ALLOWED_ORDER_TRANSITIONS.get(from_status, set())
            BackgroundCheckOrderEvent.objects.create(
                order=order, config=config, from_status=from_status,
                to_status=BGOrderStatus.CANCELLED, source='CANCEL',
                is_legal_transition=is_legal, raw_payload={'number': order.order_number},
            )
            order.status = BGOrderStatus.CANCELLED
            order.status_name = BGOrderStatus.CANCELLED.label
            order.save(update_fields=['status', 'status_name', 'updated_at'])
    except Exception as e:
        logger.exception('cancel_background_check_order failed')
        result = {'success': False, 'message': f'取消异常: {e}'}
    return result


def verify_background_check_callback(payload: dict, app_id: str) -> tuple[bool, int, str, Optional[IntegrationConfig]]:
    """校验背调供应商异步回调（规范 §5.2 验签 + 重放防护）。

    参数:
        payload: 供应商回调请求体（已解析 dict）
        app_id: 请求头 X-App-Id（供应商 appId）
    返回:
        (ok, code, message, config)
        - ok=True 时 config 为命中的 IntegrationConfig
        - ok=False 时按 §4.2 返回业务码 40101(无效appId)/40102(签名失败)/40103(重放)/40001(缺参)
    """
    # 1. 必填字段校验（§2.2.5 必需 + §5.2 签名公式依赖 timestamp）
    #    注意: §2.2.5 字段表未列 timestamp, 但 §5.2 签名公式依赖它, 故强制要求, 缺失即拒。
    number = payload.get('number')
    status_val = payload.get('status')
    ts = payload.get('timestamp')
    sign = payload.get('sign')
    if not number or status_val is None or ts is None or not sign:
        return False, 40001, '缺少必填字段(number/status/timestamp/sign)', None

    # 2. 按 X-App-Id 定位已启用的背调供应商配置
    matched: Optional[IntegrationConfig] = None
    for c in IntegrationConfig.objects.filter(type=IntegrationType.BACKGROUND_CHECK, is_active=True):
        cfg_app_id = (c.config or {}).get('AppId') or (c.config or {}).get('appId')
        if cfg_app_id and cfg_app_id == app_id:
            matched = c
            break
    if matched is None:
        return False, 40101, 'appId 无效或未匹配到供应商', None

    # 3. 解密 appKey（与出向签名同源：api_key 或 apiKey）
    secret = _bg_secret(matched)
    app_key = secret.get('api_key') or secret.get('apiKey') or ''
    if not app_key:
        return False, 40102, '供应商未配置 appKey(签名失败)', matched

    # 4. 重放防护: ±5 分钟（§5.2）
    try:
        ts_int = int(ts)
    except (TypeError, ValueError):
        return False, 40001, 'timestamp 非法', matched
    now_ms = int(time.time() * 1000)
    if abs(now_ms - ts_int) > 5 * 60 * 1000:
        return False, 40103, '时间戳超时(疑似重放)', matched

    # 5. 重算签名并比对（§5.2 待签串: number=&status=&timestamp=）
    sign_str = "number=" + str(number) + "&status=" + str(status_val) + "&timestamp=" + str(ts_int)
    expect = hmac.new(app_key.encode('utf-8'), sign_str.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, str(sign).lower()):
        return False, 40102, '签名校验失败', matched

    return True, 0, 'success', matched


def bg_callback_envelope(code: int, message: str, data: Optional[dict] = None, request_id: Optional[str] = None) -> dict:
    """统一回调响应信封（规范 §3.2）。

    - 成功: code=0, HTTP 200
    - 失败: code≠0, HTTP 401（见视图层）, 但信封结构一致
    """
    return {
        'code': code,
        'message': message,
        'data': data or {},
        'requestId': request_id or str(uuid.uuid4()),
        'timestamp': int(time.time() * 1000),
    }


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
