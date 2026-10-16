"""动态取值条件（valueSource='dynamic'）穿透真实 HTTP 链路的回归。

## 背景（2026-10-16 兵哥「已经全部都设置了，为什么不能保存」）

管理员在「操作权限」页签给需求模块配写范围：条件「TBP 包含 当前登录用户」，
取值来源明明选了动态，保存却报：

    模块 demand 写范围: 条件组 1 第 1 条：请为每条条件选择业务值

## 根因

项目 REST_FRAMEWORK 装的是 `CamelCaseJSONParser`，它对**请求体**递归
underscoreize：`valueSource→value_source`、`dynamicKey→dynamic_key`。
而数据权限模块全链路按 camelCase 读条件键，于是动态条件在到达业务逻辑前
就丢了 `valueSource`：
  - `validate_scope_payload` 取不到 → 落进静态分支 → 报"请选择业务值"；
  - `expr_compiler` 编译期同样取不到 → 即便绕过校验落库，动态条件也会
    退化成 no-op（可见/可写范围恒为空）。

## 为什么历史测试没抓到

既有单测（test_m03_unit_dynamic.py 等）**直接构造 camelCase dict 调用函数层**，
绕过了 URL 路由与 request.data 解析，动态分支永远走不到。本文件一律用
Django test client 打真实 URL，让 payload 原样过一遍 CamelCaseJSONParser。

## 反假绿纪律（DR-01）

每条用例都先断言「落库的 scope_payload 里条件确实带 valueSource/dynamicKey」，
再断言业务语义；否则「保存成功但字段是空的」也会被判绿。
"""
import json

import pytest
from django.test import Client

from apps.core.models import User
from apps.core.models_permission_v2 import RoleV2
from apps.data_permission.models import DataPermissionRule

ROLE_CODE = 'QA_DYNAMIC_HTTPPARSER'
DP_URL = '/api/v1/roles/{pk}/data-permissions/'


@pytest.fixture
def role(db):
    return RoleV2.objects.create(
        system_code='recruit', role_code=ROLE_CODE,
        role_name='QA 动态取值解析器回归', status=1,
    )


@pytest.fixture
def admin_client(db):
    user = User.objects.create(username='qa_dyn_admin', is_superuser=True, is_active=True)
    from rest_framework_simplejwt.tokens import RefreshToken
    c = Client()
    c._qa_token = 'Bearer ' + str(RefreshToken.for_user(user).access_token)
    return c


def _post(client, role, modules):
    """打真实 HTTP POST（payload 原样过 CamelCaseJSONParser），返回 (status, json)。"""
    resp = client.post(
        DP_URL.format(pk=role.pk),
        data=json.dumps({'modules': modules}),
        content_type='application/json',
        HTTP_AUTHORIZATION=client._qa_token,
    )
    try:
        body = resp.json()
    except Exception:  # pragma: no cover - 仅在非 JSON 响应时
        body = {'_raw': resp.content[:300].decode('utf-8', 'replace')}
    return resp.status_code, body


def _dynamic_cond(cid, dimension='tbp'):
    """与前端 RuleConfigModal.cloneGroups 产出同形的动态条件（camelCase）。"""
    return {
        'id': cid, 'kind': 'relationship', 'dimension': dimension,
        'operator': 'in', 'valueSource': 'dynamic',
        'dynamicKey': 'currentUser.id', 'values': [],
    }


def _payload(mode='all', write_groups=None, groups=None):
    m = {'moduleKey': 'demand', 'mode': mode, 'expr': '', 'groups': groups or []}
    if write_groups is not None:
        m['write'] = {
            'mode': 'scope', 'expr': '1',
            'groups': [{
                'id': 'g1', 'expr': '1 or 2',
                'conditions': [_dynamic_cond('c1', 'tbp'), _dynamic_cond('c2', 'hrbp')],
            }],
            'actions': ['edit', 'create'],
        }
    return [m]


def _write_payload_of(role_code):
    r = DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role_code,
        level='ROW', row_access='WRITE', entity='demand',
    ).first()
    return r


# ============ 写范围：动态条件可保存（本次报障现场） ============

def test_write_scope_dynamic_condition_saves(admin_client, role):
    """写范围动态条件 POST 应 200，且落库条件保留 camelCase 的 valueSource/dynamicKey。"""
    status, body = _post(admin_client, role, _payload(write_groups=True))
    assert status == 200, f'动态写范围被拒 HTTP {status}: {body}'
    assert body.get('success') is True, body

    row = _write_payload_of(role.role_code)
    assert row is not None, '写范围未落库——后续断言将恒真，用例无鉴别力'
    cond = row.scope_payload['groups'][0]['conditions'][0]
    assert cond.get('valueSource') == 'dynamic', f'落库条件丢了 valueSource: {cond}'
    assert cond.get('dynamicKey') == 'currentUser.id', f'落库条件丢了 dynamicKey: {cond}'


def test_write_scope_dynamic_condition_read_back(admin_client, role):
    """再 GET 一次：读接口回显的 groups 键名必须仍是 camelCase（前端按 camelCase 消费）。"""
    status, _ = _post(admin_client, role, _payload(write_groups=True))
    assert status == 200

    resp = admin_client.get(
        DP_URL.format(pk=role.pk), HTTP_AUTHORIZATION=admin_client._qa_token,
    )
    body = resp.json()
    demand = next(m for m in body['data']['modules'] if m['moduleKey'] == 'demand')
    cond = demand['write']['groups'][0]['conditions'][0]
    assert cond.get('valueSource') == 'dynamic', f'读回显丢了 valueSource: {cond}'


# ============ 读范围：同一 bug 也存在于读侧 ============

def test_read_scope_dynamic_condition_saves(admin_client, role):
    """读范围动态条件同样受影响（同一解析器），必须一并可存。"""
    groups = [{
        'id': 'g1', 'expr': '1',
        'conditions': [_dynamic_cond('c1', 'tbp')],
    }]
    status, body = _post(admin_client, role, _payload(mode='scope', groups=groups))
    assert status == 200, f'动态读范围被拒 HTTP {status}: {body}'

    row = DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role.role_code,
        level='ROW', row_access__isnull=True, entity='demand',
    ).first()
    assert row is not None, '读范围未落库'
    cond = row.scope_payload['groups'][0]['conditions'][0]
    assert cond.get('valueSource') == 'dynamic', f'落库条件丢了 valueSource: {cond}'


# ============ 反向锚点：静态条件仍按原语义校验（防放宽过头） ============

def test_static_condition_without_value_still_rejected(admin_client, role):
    """静态条件不选业务值 → 仍应 400（证明修复只补键名还原，没有放宽校验）。"""
    groups = [{
        'id': 'g1', 'expr': '1',
        'conditions': [{
            'id': 'c1', 'kind': 'relationship', 'dimension': 'tbp',
            'operator': 'in', 'values': [],
        }],
    }]
    status, body = _post(admin_client, role, _payload(mode='scope', groups=groups))
    assert status == 400, f'静态空值条件应被拒，实际 HTTP {status}: {body}'
    assert '请为每条条件选择业务值' in (body.get('message') or ''), body


def test_dynamic_source_not_applicable_dimension_rejected(admin_client, role):
    """动态来源不适配该维度 → 仍应 400（键名还原后这段校验才真正生效）。"""
    groups = [{
        'id': 'g1', 'expr': '1',
        # lock_owner 只支持 currentUser.id；用 dept 专属的 currentUser.deptSubtree 试
        'conditions': [{
            'id': 'c1', 'kind': 'relationship', 'dimension': 'tbp',
            'operator': 'in', 'valueSource': 'dynamic',
            'dynamicKey': 'currentUser.deptSubtree', 'values': [],
        }],
    }]
    status, body = _post(admin_client, role, _payload(mode='scope', groups=groups))
    assert status == 400, f'不适配的动态来源应被拒，实际 HTTP {status}: {body}'