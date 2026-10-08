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

import binascii
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
from django.db import IntegrityError, OperationalError
from django.utils import timezone

from apps.common.exceptions import NotFound
from apps.common.encryption import DecryptionError
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
from .serializers import BackgroundCheckOrderSerializer

# T6: 背调供应商统一适配器（HMAC 双签 / 状态机 / query+report 接口）
from .suppliers.factory import get_supplier
from .suppliers.base import (
    BaseBackgroundCheckSupplier,
    CreateOrderRequest,
    verify_callback_signature,
    replay_allowed,
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
        except (ValueError, json.JSONDecodeError, TypeError, binascii.Error, DecryptionError) as e:
            # 解密失败 (fail-closed DecryptionError) 仍记为失败: 仅兜解密/解析窄集异常,
            # 编程错误 (AttributeError/NameError) 仍向上抛以便排查. 密钥配错时 secret_dict 置空,
            # 调用方 (send_email 等) 会因缺凭证优雅失败 + 记日志, 不静默返空串误导.
            logger.exception('IntegrationConfig %s: decrypt failed: %s', integration_type, e)
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
    except (smtplib.SMTPException, OSError, ConnectionError, TimeoutError, KeyError) as e:
        # SMTP 协议 + 网络 IO + 地址解析异常窄集. 编程错误不再吞, 向上抛以便排查.
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
        except OperationalError:
            # ORM 落库失败仍吞, 避免 audit 写失败再触发外层 500 (此处已是 send_email 失败路径).
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
    except (ConnectionError, TimeoutError, OSError, requests.RequestException, ValueError) as e:
        # 短信 IO / HTTP SDK / 参数异常窄集.
        logger.exception('SMS send failed: %s', e)
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
    except (ConnectionError, TimeoutError, OSError, requests.RequestException, ValueError) as e:
        # 阿里云短信 HTTPS 请求 + JSON 解析窄集. base64/编码错误归 ValueError.
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
    except (ConnectionError, TimeoutError, OSError, requests.RequestException, ValueError) as e:
        # 企微应用消息 HTTP + JSON 解析窄集.
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
    except (ConnectionError, TimeoutError, OSError, requests.RequestException, ValueError) as e:
        # 企微群机器人 webhook HTTP + JSON 解析窄集.
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
    except (ConnectionError, TimeoutError, OSError, requests.RequestException, ValueError) as e:
        # Moka HTTP GET + JSON 解析窄集.
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
    except (ConnectionError, TimeoutError, OSError, requests.RequestException, ValueError) as e:
        # Moka HTTP POST + JSON 解析窄集.
        logger.exception('Moka push failed: %s', e)
        return {'success': False, 'error': str(e)}


# ============================================================
# 背调（统一规范 v1.0.1：HMAC-SHA256 双向签名 + 调用审计）
# T6: HMAC 双签 / 路径 / appId-appKey 解析已收敛到 suppliers 包；
#     本模块仅保留平台侧职责（验签入口 / 状态机 / 审计日志 / 对外 dict）。
# ============================================================


def test_background_check_connection(config: IntegrationConfig) -> Dict[str, Any]:
    """测试连接：T6 委托供应商适配器做套餐查询（带 HMAC 签名），校验连通性与凭证。

    审计 IntegrationSyncLog(sync_type=TEST_CONNECTION) 仍由本函数落库，保持对外行为一致。
    """
    try:
        supplier = get_supplier(config)
        if not supplier._app_id or not supplier._app_key:
            return {'success': False, 'message': '缺少 appId / appKey 配置'}
        if not supplier._base_url:
            return {'success': False, 'message': '未配置 BaseURL'}
        res = supplier.query_products()  # BackgroundCheckResult
        IntegrationSyncLog.objects.create(
            config=config, sync_type='TEST_CONNECTION',
            status='SUCCESS' if res.success else 'FAILED',
            endpoint=supplier.PRODUCTS_PATH, method='GET', direction='OUT',
            duration_ms=res.duration_ms,
            error_message='' if res.success else (res.message or '')[:200],
        )
        return {
            'success': res.success,
            'message': '连接成功' if res.success else f'连接失败: {res.message}',
            'duration_ms': res.duration_ms,
        }
    except (OperationalError, ConnectionError, TimeoutError, OSError, ValueError) as e:
        # 供应商 adapter 委托: 网络 IO + ORM 落库 + 解析窄集.
        logger.exception('test_background_check_connection failed: %s', e)
        return {'success': False, 'message': f'测试失败: {e}'}

def request_background_check(candidate_id: str, items: List[str], config_id: str = None,
                             *, candidate_name: str = '', phone: str = '',
                             operator_name: str = '', operator_phone: str = '',
                             channel: str = 'SYSTEM_ORDER', remark: str = '',
                             parent_order_id: str = '', bg_suggestions: Optional[list] = None,
                             has_existing_report: bool = False,
                             package_name: str = '', bg_result: str = '',
                             contactable: Optional[bool] = None,
                             subject_snapshot: Optional[dict] = None,
                             expected_onboarding_date: str = '') -> Dict[str, Any]:
    """发起背调（T6 委托供应商适配器；保持对外 dict 形状与落库行为）。

    candidate_name/phone/operator_name/operator_phone 透传给供应商 CreateOrderRequest，
    用于填写规范 §3.2 必填字段（候选人姓名/手机号、委托人姓名/手机号）。
    channel/remark/parent_order_id/bg_suggestions 为步骤式弹窗扩展：无报告下单时把背调建议
    填充至订单备注（remark），补充背调标记 is_supplementary + 父订单。
    """
    try:
        qs = IntegrationConfig.objects.filter(type=IntegrationType.BACKGROUND_CHECK, is_active=True)
        if config_id:
            qs = IntegrationConfig.objects.filter(id=config_id, type=IntegrationType.BACKGROUND_CHECK)
        config = qs.first()
        if not config:
            return {'success': False, 'error': 'Background check not configured'}
        supplier = get_supplier(config)
        req = CreateOrderRequest(
            candidate_id=str(candidate_id),
            items=list(items or []),
            candidate_name=candidate_name or '',
            phone=phone or '',
            operator_name=operator_name or '',
            operator_phone=operator_phone or '',
            # 步骤式弹窗扩展：预计入职日期 → 供应商 expect_entry_time；可否联系 → contact_candidate(1/0)
            expect_entry_time=expected_onboarding_date or None,
            contact_candidate=(1 if contactable else 0) if contactable is not None else None,
        )
        res = supplier.create_order(req)
        IntegrationSyncLog.objects.create(
            config=config, sync_type='CREATE_ORDER',
            status='SUCCESS' if res.success else 'FAILED',
            endpoint=supplier.CREATE_PATH, method='POST', direction='OUT',
            duration_ms=res.duration_ms,
            error_message='' if res.success else (res.message or '')[:200],
        )
        if res.success:
            inner = (res.data or {}).get('data') or {}
            order_number = inner.get('number')
            if order_number:
                try:
                    create_background_check_order(
                        config=config, candidate_id=str(candidate_id),
                        candidate_name=candidate_name or '',
                        items=list(items or []), order_number=str(order_number),
                        request_payload=inner,
                        channel=channel, remark=remark or '',
                        is_supplementary=bool(parent_order_id),
                        parent_order_id=parent_order_id or '',
                        bg_suggestions=list(bg_suggestions or []),
                        package_name=package_name or '',
                        bg_result=bg_result or '',
                        subject_snapshot=subject_snapshot or {},
                    )
                except (OperationalError, IntegrityError) as e:
                    # audit 落库失败: 单订单级别兜底, 不阻断上层返 success (供应商已收单).
                    logger.exception(
                        'create_background_check_order failed (number=%s): %s', order_number, e,
                    )
            return {'success': True, 'data': res.data}
        return {'success': False, 'error': res.message}
    except (OperationalError, IntegrityError, ConnectionError, TimeoutError,
            requests.RequestException, ValueError) as e:
        # 供应商委托 + ORM 落库 + 网络 IO 窄集. 编程错误不再吞.
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
                                  request_payload: Optional[dict] = None,
                                  *, channel: str = 'SYSTEM_ORDER', remark: str = '',
                                  is_supplementary: bool = False, parent_order_id: str = '',
                                  bg_suggestions: Optional[list] = None,
                                  package_name: str = '', bg_result: str = '',
                                  subject_snapshot: Optional[dict] = None) -> BackgroundCheckOrder:
    """落初始背调订单（状态机起点 status=0 已受理）。

    幂等：同一 (config, order_number) 已存在则直接返回，不重复写 CREATE 事件。
    channel/remark/is_supplementary/parent_order_id/bg_suggestions 为步骤式弹窗扩展字段。
    package_name/bg_result/subject_snapshot 为下单分支冗余/快照字段。
    返回 BackgroundCheckOrder。
    """
    order, created = BackgroundCheckOrder.objects.get_or_create(
        config=config, order_number=str(order_number),
        defaults={
            'candidate_id': str(candidate_id or ''),
            'candidate_name': candidate_name or '',
            'status': BGOrderStatus.ACCEPTED,
            'status_name': BGOrderStatus.ACCEPTED.label,
            'channel': channel,
            'remark': remark or '',
            'is_supplementary': bool(is_supplementary),
            'parent_order_id': parent_order_id or '',
            'bg_suggestions': list(bg_suggestions or []),
            'package_name': package_name or '',
            'bg_result': bg_result or '',
            'subject_snapshot': subject_snapshot or {},
            'latest_payload': request_payload,
        },
    )
    if created:
        BackgroundCheckOrderEvent.objects.create(
            order=order, config=config, from_status=None, to_status=BGOrderStatus.ACCEPTED,
            source='CREATE', is_legal_transition=True, raw_payload=request_payload,
        )
    return order


def upload_background_check_report(candidate_id: str, candidate_name: str = '', phone: str = '',
                                   report_url: str = '', remark: str = '',
                                   answers: Optional[list] = None,
                                   bg_suggestions: Optional[list] = None,
                                   parent_order_id: str = '',
                                   operator_name: str = '',
                                   package_name: str = '', bg_provider: str = '',
                                   bg_time: str = '', bg_result: str = '',
                                   subject_snapshot: Optional[dict] = None) -> Dict[str, Any]:
    """已有报告上传 / 自主背调（步骤式弹窗「已有报告」分支）。

    不调用供应商接口，直接落一条 channel=SELF、status=已完成(1) 的订单，
    承载上传的报告地址与背调建议回答（answers 回填至 bg_suggestions 的 answer 字段）。
    上传分支冗余/快照字段：package_name/bg_provider/bg_time/bg_result/subject_snapshot。
    补充背调时 parent_order_id 非空，置 is_supplementary=True。
    """
    try:
        from django.utils.dateparse import parse_datetime
        # 合并面试官背调建议与招聘专家回答
        suggestions = list(bg_suggestions or [])
        answer_map = {a.get('interviewer') or a.get('id'): a.get('answer', '') for a in (answers or [])}
        for s in suggestions:
            key = s.get('interviewer') or s.get('id')
            if key in answer_map:
                s['answer'] = answer_map[key]

        # bg_time：ISO 字符串 → 时区感知 datetime（非法/空 → None）
        parsed_bg_time = parse_datetime(bg_time) if bg_time else None

        order = BackgroundCheckOrder.objects.create(
            config=None,  # 自主背调无供应商配置
            candidate_id=str(candidate_id or ''),
            candidate_name=candidate_name or '',
            channel=BGChannel.SELF,
            order_number=f'SELF-{nanoid_generate(size=16).upper()}',
            status=BGOrderStatus.COMPLETED,
            status_name=BGOrderStatus.COMPLETED.label,
            report_url=report_url or '',
            completion_time=timezone.now(),
            remark=remark or '',
            is_supplementary=bool(parent_order_id),
            parent_order_id=parent_order_id or '',
            bg_suggestions=suggestions,
            package_name=package_name or '',
            bg_provider=bg_provider or '',
            bg_time=parsed_bg_time,
            bg_result=bg_result or '',
            subject_snapshot=subject_snapshot or {},
            latest_payload={'operator_name': operator_name or '', 'upload': True},
        )
        BackgroundCheckOrderEvent.objects.create(
            order=order, config=None, from_status=None, to_status=BGOrderStatus.COMPLETED,
            source='CREATE', is_legal_transition=True,
            report_url=report_url or '', completion_time=order.completion_time,
            raw_payload={'upload': True, 'report_url': report_url or ''},
        )
        return {'success': True, 'data': BackgroundCheckOrderSerializer(order).data}
    except (OperationalError, IntegrityError, ValueError) as e:
        # 自主上传落库窄集. 编程错误不再吞.
        logger.exception('upload_background_check_report failed: %s', e)
        return {'success': False, 'error': str(e)}


# 背调建议兜底示例：真实面试官提交的建议为空时，供前端表单演示/联调使用。
# 一旦存在任何真实建议，即完全不启用本兜底（保证真实数据优先，不污染业务语义）。
_BG_SUGGESTION_DEMO_FALLBACK: List[Dict[str, Any]] = [
    {
        'interviewer': 'demo-1',
        'interviewer_name': '李经理（技术面试官）',
        'interview_id': '',
        'suggestion': '重点核实候选人在上一段工作中承担的核心职责，以及离职原因是否与简历描述一致。',
        'submitted_at': '',
    },
    {
        'interviewer': 'demo-2',
        'interviewer_name': '王主管（用人经理）',
        'interview_id': '',
        'suggestion': '请核实其管理团队的实际规模与汇报关系，确认是否具备独立带团队的能力。',
        'submitted_at': '',
    },
    {
        'interviewer': 'demo-3',
        'interviewer_name': '赵老师（HR）',
        'interview_id': '',
        'suggestion': '核对在职时间与社保缴纳记录是否吻合，并确认是否存在竞业限制协议。',
        'submitted_at': '',
    },
]


def aggregate_bg_suggestions(candidate_id: str) -> List[Dict[str, Any]]:
    """聚合某候选人来自各面试官的背调建议（按面试官去重，取最新一条）。

    返回 [{interviewer, interviewer_name, interview_id, suggestion, submitted_at}]。

    兜底策略：若该候选人尚无任何真实背调建议，返回 3 条内置示例，
    便于前端表单展示与联调；一旦有真实建议，示例立即被替换。
    """
    from apps.interview.models import InterviewEvaluation
    evals = (
        InterviewEvaluation.objects
        .filter(interview__application__candidate_id=str(candidate_id), deleted_at__isnull=True)
        .exclude(bg_suggestion__exact='')
        .select_related('interviewer', 'interview', 'interview__application')
        .order_by('interviewer_id', '-submitted_at')
    )
    seen = {}
    for ev in evals:
        iid = ev.interviewer_id
        if iid in seen:
            continue
        seen[iid] = {
            'interviewer': iid,
            'interviewer_name': getattr(ev.interviewer, 'username', '') or '',
            'interview_id': ev.interview_id,
            'suggestion': ev.bg_suggestion or '',
            'submitted_at': ev.submitted_at.isoformat() if ev.submitted_at else '',
        }
    if not seen:
        return [dict(item) for item in _BG_SUGGESTION_DEMO_FALLBACK]
    return list(seen.values())


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

    T6: 先委托供应商适配器做签名出向（best-effort），再在平台侧置为已取消。
    平台发起的取消具有权威性，无论出向成败均落 CANCEL 事件。
    """
    config = config or order.config
    result: Dict[str, Any] = {'success': True, 'message': '已取消'}
    try:
        supplier = get_supplier(config)
        if supplier._base_url and supplier._app_key:
            res = supplier.cancel_order(order.order_number)
            IntegrationSyncLog.objects.create(
                config=config, sync_type='CANCEL_ORDER',
                status='SUCCESS' if res.success else 'FAILED',
                endpoint=supplier.CANCEL_PATH, method='POST', direction='OUT',
                duration_ms=res.duration_ms,
                error_message='' if res.success else (res.message or '')[:200],
            )
            if not res.success:
                result = {'success': False,
                          'message': f'供应商取消失败: {res.message}'}

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
    except (OperationalError, IntegrityError, ConnectionError, TimeoutError,
            requests.RequestException, ValueError) as e:
        # 取消订单: 供应商出向 + ORM 落库窄集. result 仍返对外 dict.
        logger.exception('cancel_background_check_order failed: %s', e)
        result = {'success': False, 'message': f'取消异常: {e}'}
    return result

def verify_background_check_callback(payload: dict, app_id: str) -> tuple[bool, int, str, Optional[IntegrationConfig]]:
    """校验背调供应商异步回调（规范 §5.2 验签 + 重放防护）。

    参数 / 返回 同原实现；签名公式与重放窗口判定已收敛到 suppliers.base
    （verify_callback_signature / replay_allowed），本函数保留 appId 定位与编排。
    """
    # 1. 必填字段校验（§2.2.5 必需 + §5.2 签名公式依赖 timestamp）
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
    app_key = BaseBackgroundCheckSupplier._resolve_app_key(
        BaseBackgroundCheckSupplier._load_secret(matched)
    )
    if not app_key:
        return False, 40102, '供应商未配置 appKey(签名失败)', matched

    # 4. 重放防护: ±5 分钟（§5.2）
    try:
        ts_int = int(ts)
    except (TypeError, ValueError):
        return False, 40001, 'timestamp 非法', matched
    if not replay_allowed(ts_int):
        return False, 40103, '时间戳超时(疑似重放)', matched

    # 5. 重算签名并比对（§5.2 待签串: number=&status=&timestamp=）
    if not verify_callback_signature(payload, app_key):
        return False, 40102, '签名校验失败', matched

    return True, 0, 'success', matched


def query_background_check_order(order_number: str, config_id: str = None) -> Dict[str, Any]:
    """主动轮询供应商订单最新状态（§6.4 兜底；T6 新增接口）。

    委托供应商适配器 query_order（GET 订单详情），落审计日志后返回统一 dict。
    """
    try:
        qs = IntegrationConfig.objects.filter(type=IntegrationType.BACKGROUND_CHECK, is_active=True)
        if config_id:
            qs = IntegrationConfig.objects.filter(id=config_id, type=IntegrationType.BACKGROUND_CHECK)
        config = qs.first()
        if not config:
            return {'success': False, 'error': 'Background check not configured'}
        supplier = get_supplier(config)
        res = supplier.query_order(order_number)
        IntegrationSyncLog.objects.create(
            config=config, sync_type='QUERY_ORDER',
            status='SUCCESS' if res.success else 'FAILED',
            endpoint=supplier.ORDER_DETAIL_PATH.format(number=order_number),
            method='GET', direction='OUT', duration_ms=res.duration_ms,
            error_message='' if res.success else (res.message or '')[:200],
        )
        return {
            'success': res.success,
            'message': res.message,
            'data': res.data,
            'duration_ms': res.duration_ms,
        }
    except (OperationalError, ConnectionError, TimeoutError, requests.RequestException, ValueError) as e:
        # 主动轮询: ORM 落库 + 供应商 HTTP 窄集.
        logger.exception('query_background_check_order failed: %s', e)
        return {'success': False, 'error': str(e)}


def fetch_background_check_report(order: 'BackgroundCheckOrder') -> Dict[str, Any]:
    """拉取背调报告（T6 新增接口）。

    委托供应商适配器 fetch_report（GET order.report_url），落审计日志后返回统一 dict。
    """
    try:
        config = order.config
        supplier = get_supplier(config)
        res = supplier.fetch_report(order)
        IntegrationSyncLog.objects.create(
            config=config, sync_type='FETCH_REPORT',
            status='SUCCESS' if res.success else 'FAILED',
            endpoint=order.report_url or '', method='GET', direction='OUT',
            duration_ms=res.duration_ms,
            error_message='' if res.success else (res.message or '')[:200],
        )
        return {
            'success': res.success,
            'message': res.message,
            'data': res.data,
            'duration_ms': res.duration_ms,
        }
    except (OperationalError, ConnectionError, TimeoutError, requests.RequestException, ValueError) as e:
        # 拉取报告: ORM 落库 + 供应商 HTTP 窄集.
        logger.exception('fetch_background_check_report failed: %s', e)
        return {'success': False, 'error': str(e)}

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
    except (ConnectionError, TimeoutError, OSError, requests.RequestException, ValueError) as e:
        # 招聘门户 HTTP POST + JSON 解析窄集.
        logger.exception('Portal sync failed: %s', e)
        return {'success': False, 'error': str(e)}
