"""审计日志请求体脱敏测试.

背景 (2026-10-08 审查 F-18):
    `AuditMiddleware._record` 在 DEBUG 下直接 `request.body[:512]` 写日志,
    而 dev.py 把 apps logger 设为 DEBUG —— 登录密码、refresh token、验证码、
    手机号/邮箱/身份证会原样落进日志。日志被共享/备份/采集即等于明文凭据泄露。
"""
import json

import pytest
from django.test import RequestFactory

from apps.audit.middleware import safe_body_summary


@pytest.fixture
def rf():
    return RequestFactory()


def _post(rf, path, payload, **kwargs):
    return rf.post(path, data=json.dumps(payload),
                   content_type='application/json', **kwargs)


# ---------------------------------------------------------------- 敏感端点整体跳过

@pytest.mark.parametrize('path', [
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/api/v1/auth/change-password',
    '/api/v1/auth/refresh',
    '/api/v1/gdpr/requests/',
])
def test_sensitive_endpoints_omit_body_entirely(rf, path):
    req = _post(rf, path, {'username': 'u', 'password': 'P@ssw0rd!'})
    summary = safe_body_summary(req)
    assert 'P@ssw0rd!' not in summary
    assert summary == '<omitted: sensitive endpoint>'


# ---------------------------------------------------------------- 值一律脱敏

def test_password_value_never_appears(rf):
    req = _post(rf, '/api/v1/candidates/', {
        'name': '张三', 'password': 'SuperSecret123',
    })
    summary = safe_body_summary(req)
    assert 'SuperSecret123' not in summary
    assert '张三' not in summary, '非敏感字段的值同样不应原样落日志'


def test_phone_email_idcard_never_appear(rf):
    req = _post(rf, '/api/v1/candidates/', {
        'phone': '13800001111',
        'email': 'victim@example.com',
        'id_card_no': '110101199001011234',
        'name': '李四',
    })
    summary = safe_body_summary(req)
    for leak in ('13800001111', 'victim@example.com', '110101199001011234', '李四'):
        assert leak not in summary, f'{leak} 泄漏到了日志摘要'


def test_token_and_refresh_never_appear(rf):
    req = _post(rf, '/api/v1/xxx/', {
        'refresh': 'eyJhbGciOiJIUzI1NiJ9.aaaa.bbbb',
        'access_token': 'eyJccc.ddd',
    })
    summary = safe_body_summary(req)
    assert 'eyJ' not in summary
    assert 'aaaa' not in summary


def test_structure_is_preserved(rf):
    """脱敏后仍保留"提交了哪些字段"的结构信息, 便于排查问题。"""
    req = _post(rf, '/api/v1/candidates/', {'name': '王五', 'age': 30})
    summary = safe_body_summary(req)
    parsed = json.loads(summary)
    assert set(parsed) == {'name', 'age'}
    assert parsed['age'] == '<num>'


def test_nested_and_list_structures(rf):
    req = _post(rf, '/api/v1/xxx/', {
        'items': [{'phone': '13800002222'}, {'name': 'a'}],
        'meta': {'deep': {'password': 'x'}},
    })
    summary = safe_body_summary(req)
    assert '13800002222' not in summary
    assert 'x' not in summary or '"password": "<redacted>"' in summary


# ---------------------------------------------------------------- 其他分支

def test_get_request_returns_empty(rf):
    req = rf.get('/api/v1/candidates/')
    assert safe_body_summary(req) == ''


def test_non_json_body_omitted(rf):
    req = rf.post('/api/v1/upload/', data='raw text', content_type='text/plain')
    assert safe_body_summary(req) == '<omitted: non-json body>'


def test_large_body_omitted(rf):
    req = _post(rf, '/api/v1/xxx/', {'blob': 'A' * 20000})
    assert 'too large' in safe_body_summary(req)


def test_empty_body(rf):
    # 注意: 必须显式给 content_type —— RequestFactory.post 默认用 multipart,
    # 空 data 也会生成 boundary 文本, 那样命中的是"非 JSON"分支。
    req = rf.post('/api/v1/xxx/', data='', content_type='application/json')
    assert safe_body_summary(req) == ''


def test_multipart_upload_body_omitted(rf):
    """multipart (文件上传) 结构不可控, 整体跳过而不是截断记录。"""
    # 不指定 content_type → RequestFactory 用 multipart, body 含 boundary 文本
    req = rf.post('/api/v1/xxx/', {'field': 'value'})
    assert safe_body_summary(req) == '<omitted: non-json body>'
