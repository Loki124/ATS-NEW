"""信封契约测试：campus_control 四件套（维度 / 指标 / 规则 / 人员）。

Batch 11 协调批：
- 后端 ControlDimensionViewSet / ControlIndicatorViewSet / ControlRuleViewSet / PersonViewSet
  均套 EnvelopeWriteMixin（create→201 / update·partial_update / retrieve 包 {success,data} 信封）。
- 前端 campusControl.ts 的 6 处单对象 CRUD + upsertPerson 两分支已裸容错
  (r.data?.data ?? r.data)。

本测试锁住四条路由的 list / retrieve / update / create 信封形状，并验证：
- create 仍返 201、响应体为 {success,data,...}（data 为对象，非裸对象）；
- update(PATCH) 仍返 200、响应体包 envelope；
- retrieve 返 envelope；
- list 返 envelope（含 data 列表）。
"""
import uuid

import pytest

from apps.campus_control.models import (
    ControlDimension, ControlIndicator, ControlRule, Person,
)

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus'


# —— 工厂（预置对象走 ORM，非被测路径；用唯一后缀避免 unique 碰撞）——
def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _make_dimension(user):
    return ControlDimension.objects.create(name=f'维度_{_uid()}', created_by=user, updated_by=user)


def _make_indicator(dim, user):
    return ControlIndicator.objects.create(
        dimension=dim, name=f'指标_{_uid()}', created_by=user, updated_by=user,
    )


def _make_rule(dim, ind, user):
    return ControlRule.objects.create(
        dimension=dim, indicator=ind, year=2026, target=1.0, strength='软约束',
        annual_target=0, monthly_targets=[0] * 12, is_active=True,
        created_by=user, updated_by=user,
    )


def _make_person(user):
    return Person.objects.create(
        code=f'C{_uid()}', name='张三', bu='能电BG', school='985', sex='男',
        major='工学', month='1月', status='在职', created_by=user, updated_by=user,
    )


# —— 断言 helper ——
def _assert_envelope(body: dict) -> None:
    assert body.get('success') is True
    assert body.get('code') == 0
    assert 'data' in body


# ===================== 维度 =====================
def test_dimension_list_envelope(auth_client, super_user):
    _make_dimension(super_user)
    resp = auth_client.get(f'{BASE}/dimensions/', {'page_size': 200})
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], list)


def test_dimension_create_and_retrieve_envelope(auth_client, super_user):
    resp = auth_client.post(f'{BASE}/dimensions/', {'name': f'维度_{_uid()}'})
    assert resp.status_code == 201
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], dict)
    assert 'id' in body['data']
    did = body['data']['id']

    r2 = auth_client.get(f'{BASE}/dimensions/{did}/')
    assert r2.status_code == 200
    _assert_envelope(r2.json())
    assert r2.json()['data']['id'] == did


def test_dimension_update_envelope(auth_client, super_user):
    dim = _make_dimension(super_user)
    resp = auth_client.patch(f'{BASE}/dimensions/{dim.id}/', {'name': f'维度_{_uid()}'})
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert body['data']['id'] == str(dim.id)


# ===================== 指标 =====================
def test_indicator_list_envelope(auth_client, super_user):
    dim = _make_dimension(super_user)
    _make_indicator(dim, super_user)
    resp = auth_client.get(f'{BASE}/indicators/', {'page_size': 200})
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], list)


def test_indicator_create_and_retrieve_envelope(auth_client, super_user):
    dim = _make_dimension(super_user)
    resp = auth_client.post(f'{BASE}/indicators/', {'dimension': str(dim.id), 'name': f'指标_{_uid()}'})
    assert resp.status_code == 201
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], dict)
    assert 'id' in body['data']
    iid = body['data']['id']

    r2 = auth_client.get(f'{BASE}/indicators/{iid}/')
    assert r2.status_code == 200
    _assert_envelope(r2.json())
    assert r2.json()['data']['id'] == iid


def test_indicator_update_envelope(auth_client, super_user):
    dim = _make_dimension(super_user)
    ind = _make_indicator(dim, super_user)
    resp = auth_client.patch(f'{BASE}/indicators/{ind.id}/', {'name': f'指标_{_uid()}'})
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert body['data']['id'] == str(ind.id)


# ===================== 规则 =====================
def test_rule_list_envelope(auth_client, super_user):
    dim = _make_dimension(super_user)
    ind = _make_indicator(dim, super_user)
    _make_rule(dim, ind, super_user)
    resp = auth_client.get(f'{BASE}/rules/', {'page_size': 200})
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], list)


def test_rule_create_and_retrieve_envelope(auth_client, super_user):
    dim = _make_dimension(super_user)
    ind = _make_indicator(dim, super_user)
    payload = {
        'dimension': str(dim.id),
        'indicator': str(ind.id),
        'year': 2026,
        'target': 1.0,
        'strength': '软约束',
        'annual_target': 0,
        'monthly_targets': [0] * 12,
    }
    resp = auth_client.post(f'{BASE}/rules/', payload)
    assert resp.status_code == 201
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], dict)
    assert 'id' in body['data']
    rid = body['data']['id']

    r2 = auth_client.get(f'{BASE}/rules/{rid}/')
    assert r2.status_code == 200
    _assert_envelope(r2.json())
    assert r2.json()['data']['id'] == rid


def test_rule_update_envelope(auth_client, super_user):
    dim = _make_dimension(super_user)
    ind = _make_indicator(dim, super_user)
    rule = _make_rule(dim, ind, super_user)
    # 规则序列化器 validate 在部分更新时仍要求 target（不回落 instance），故显式带上
    resp = auth_client.patch(f'{BASE}/rules/{rule.id}/', {'strength': '硬约束', 'target': 1.0})
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert body['data']['id'] == str(rule.id)
    assert body['data']['strength'] == '硬约束'


# ===================== 人员 =====================
def test_person_list_envelope(auth_client, super_user):
    _make_person(super_user)
    resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], list)


def test_person_create_and_retrieve_envelope(auth_client, super_user):
    payload = {
        'code': f'C{_uid()}',
        'name': '王五',
        'bu': '能电BG',
        'school': '985',
        'sex': '男',
        'major': '工学',
        'month': '2月',
        'status': '在职',
    }
    resp = auth_client.post(f'{BASE}/persons/', payload)
    assert resp.status_code == 201
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], dict)
    assert 'id' in body['data']
    pid = body['data']['id']

    r2 = auth_client.get(f'{BASE}/persons/{pid}/')
    assert r2.status_code == 200
    _assert_envelope(r2.json())
    assert r2.json()['data']['id'] == pid


def test_person_update_envelope(auth_client, super_user):
    person = _make_person(super_user)
    resp = auth_client.patch(f'{BASE}/persons/{person.id}/', {'name': '李四'})
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body)
    assert body['data']['id'] == str(person.id)
    assert body['data']['name'] == '李四'
