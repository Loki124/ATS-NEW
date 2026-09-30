"""信封契约 — library 院校库/专业库/公司库 ViewSet (信封 initiative Batch M).

锁定的真半信封 (标准 list / destroy 返回 {success,data} 缺 code, 经逐类直读确认):
- MajorViewSet.list / SchoolViewSet.list / CompanyViewSet.list
- MajorViewSet.destroy / SchoolViewSet.destroy

基类 EnvelopeWriteMixin 覆盖 create/update/retrieve (含 code) 但不覆盖 list/destroy,
故 list/destroy 被显式重写后仍需 success_response 补齐 code.

FE 影响面: web/app/src/api/library.ts 期望 {success, data} 信封, 仅 list 被消费;
destroy 经 admin 删除动作调用, 加 code 对 res.data.data 回退读取无破坏.

权限: V2Permission, auth_client=super_user 经 is_super_admin 短路.
"""
import uuid

import pytest

from apps.library.models import Major, School

pytestmark = pytest.mark.django_db

LIB = '/api/v1/library'
MAJORS = f'{LIB}/majors/'
SCHOOLS = f'{LIB}/schools/'
COMPANIES = f'{LIB}/companies/'


def _assert_envelope(body, *, code=0):
    assert isinstance(body, dict), f'响应非 dict: {body!r}'
    assert body.get('success') is True, f"success 非 True: {body!r}"
    assert 'data' in body, f'缺 data 键: {body!r}'
    assert body.get('code') == code, f"code 非 {code}: {body!r}"


def test_major_list_envelope(auth_client):
    """majors/ list 现返回 {success,data,code}."""
    resp = auth_client.get(MAJORS)
    assert resp.status_code == 200, resp.content
    _assert_envelope(resp.json())
    assert isinstance(resp.json()['data'], list)


def test_school_list_envelope(auth_client):
    """schools/ list 现返回 {success,data,code}."""
    resp = auth_client.get(SCHOOLS)
    assert resp.status_code == 200, resp.content
    _assert_envelope(resp.json())
    assert isinstance(resp.json()['data'], list)


def test_company_list_envelope(auth_client):
    """companies/ list 现返回 {success,data,code} (ReadOnlyModelViewSet 仅 list)."""
    resp = auth_client.get(COMPANIES)
    assert resp.status_code == 200, resp.content
    _assert_envelope(resp.json())
    assert isinstance(resp.json()['data'], list)


def test_major_destroy_envelope(auth_client):
    """majors/{id}/ DELETE 软删, 现返 {success,data:{id},code:0}."""
    major = Major.objects.create(
        id=f'mj_{uuid.uuid4().hex[:12]}',
        spec_id=f'spec_{uuid.uuid4().hex[:12]}',
        code=f'code_{uuid.uuid4().hex[:12]}',
        name='信封测试专业',
    )
    resp = auth_client.delete(f'{MAJORS}{major.id}/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    _assert_envelope(body)
    assert body['data'] == {'id': major.id}


def test_school_destroy_envelope(auth_client):
    """schools/{id}/ DELETE 软删, 现返 {success,data:{id},code:0}."""
    school = School.objects.create(
        id=f'sc_{uuid.uuid4().hex[:12]}',
        code=f'code_{uuid.uuid4().hex[:12]}',
        name='信封测试院校',
    )
    resp = auth_client.delete(f'{SCHOOLS}{school.id}/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    _assert_envelope(body)
    assert body['data'] == {'id': school.id}
