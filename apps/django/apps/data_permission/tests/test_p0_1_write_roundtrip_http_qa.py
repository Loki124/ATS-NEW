"""QA 独立验证：P0-1 写范围往返保存（穿透真实 HTTP 链路）。

## 为什么要有这个文件（与test_p0_1_write_roundtrip.py 的区别）

工程师那份测试**直接调用 `upsert_modules()` 函数**，绕过了：
  - URL 路由解析（DRF @action → url_path）
  - DRF 序列化 / request.data 解析
  - JSON null / 空对象 在传输层的真实形态
  - 视图层 `validate_modules()` 与 writeNormalized 审计

P0-1 的根因链恰恰横跨这些层（前端序列化 → JSON → 视图 → upsert）。
只在函数层断言，证明不了"真实 HTTP 请求会不会把WRITE 行抹掉"。
本文件一律用 Django test client 打真实 URL
（`POST /api/v1/roles/{id}/data-permissions/`）+ JWT 认证。

## 反假绿纪律（DR-01）

每个场景都是**两步式**断言：
  1. 先 POST 一个含 write 的 payload，断言 count == N（N 必须是 > 0）；
  2. 再 POST 待验证 payload，断言 count == N 且 id 集合不变。
若步骤 1 的 count 就是 0，则本用例无鉴别力（恒真），测试直接失败并报出来。

## 覆盖矩阵（对齐docs/ARCH_数据权限P0止血_系统设计.md §1.2.2 写范围三态判定表）

| # | payload 形态 | 期望 |
|---|---|---|
| 1 | 缺 `write` 键 | WRITE 行保留 + id 不变 + 命中哨兵 |
| 2 | `write: null` | 同上（P0-1 变种漏洞） |
| 3 | `write: {}` | 同上（P0-1 变种漏洞） |
| 4 | `write: {mode:'none'}` | WRITE 行**被删**（主动取消） |
| 5 | `write: {mode:'all',actions:[..]}` | 原地更新，id 不变（不是删了重建） |
| 6 | 角色历史无 WRITE 行 + 缺键 | 不造行 + 哨兵 [] + 不报错 |
"""
import json

import pytest
from django.test import Client

from apps.core.models import User
from apps.core.models_permission_v2 import RoleV2
from apps.data_permission.models import DataPermissionRule

ROLE_CODE = 'QA_P0_1_HTTP'
DP_URL = '/api/v1/roles/{pk}/data-permissions/'


@pytest.fixture
def role(db):
    return RoleV2.objects.create(
        system_code='recruit', role_code=ROLE_CODE,
        role_name='QA P0-1 HTTP 回归', status=1,
    )


@pytest.fixture
def admin_client(db):
    user = User.objects.create(username='qa_p0_1_admin', is_superuser=True, is_active=True)
    c = Client()
    token = _token(user)
    c._qa_token = token  # 供_call 复用
    return c


def _token(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    return 'Bearer ' + str(RefreshToken.for_user(user).access_token)


def _post(client, role, modules):
    """打真实 HTTP POST，返回 (status_code, json)。"""
    resp = client.post(
        DP_URL.format(pk=role.pk),
        data=json.dumps({'modules': modules}),
        content_type='application/json',
        HTTP_AUTHORIZATION=client._qa_token,
    )
    try:
        body = resp.json()
    except Exception:  # pragma: no cover - 仅在非 JSON 响应时
        body = {'_raw': resp.content[:200].decode('utf-8', 'replace')}
    return resp.status_code, body


def write_rows(role_code: str):
    """该角色全部 WRITE 行 -> {entity: (id, actions)}。"""
    out = {}
    for r in DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role_code,
        level='ROW', row_access='WRITE',
    ):
        out[r.entity] = (r.id, list(r.actions or []))
    return out


def _seed_write(admin_client, role, entity='candidate', actions=('edit',)):
    """先POST 一个含 write 的 payload，造出真实 WRITE 行。返回 seed 后快照。"""
    status, body = _post(admin_client, role, [
        {'moduleKey': entity, 'mode': 'all',
         'write': {'mode': 'all', 'actions': list(actions)}},
    ])
    assert status == 200, f'seed 失败 HTTP {status}: {body}'
    seeded = write_rows(role.role_code)
    assert seeded, 'seed 未产生 WRITE 行——后续"保留"断言将恒真，用例无鉴别力'
    return seeded


# ============ 场景 1：缺 write 键 ============

def test_http_missing_write_key_preserves_rule(admin_client, role):
    """payload 完全不带 write 键 → WRITE 行保留、id 不变、命中哨兵。"""
    before = _seed_write(admin_client, role)
    assert len(before) == 1, f'删前 count 应为 1，实际 {len(before)}'

    status, body = _post(admin_client, role, [{'moduleKey': 'candidate', 'mode': 'all'}])

    assert status == 200, f'缺键不应报错：HTTP {status} {body}'
    after = write_rows(role.role_code)
    assert len(after) == 1, f'WRITE 行被删：{len(before)} -> {len(after)}'
    assert after == before, f'WRITE 行被删后重建或改写：{before} -> {after}'
    assert body['data']['writeNormalized'] == ['candidate'], '应命中哨兵'
    got = next(m for m in body['data']['modules'] if m['moduleKey'] == 'candidate')
    assert got['write']['mode'] == 'all', '响应回读不应变成 none'
    assert got['write']['actions'] == ['edit']


# ============ 场景 2/3：write: null / write: {}（P0-1 变种漏洞）============

@pytest.mark.parametrize('write_value', [None, {}], ids=['null', 'empty-dict'])
def test_http_null_or_empty_write_preserves_rule(admin_client, role, write_value):
    """`write: null` / `write: {}` → WRITE 行同样必须保留。

    这两种形态是 JSON 序列化的极常见产物（前端 `write: m.write` 而 m.write
    为 undefined/null；中间层 JSON 深拷贝丢字段）。若它们被当成显式 none，
    管理员配置会被静默抹除——与P0-1 同一类数据丢失，且更难排查。
    """
    before = _seed_write(admin_client, role)
    assert len(before) == 1, f'删前 count 应为 1，实际 {len(before)}'

    status, body = _post(admin_client, role, [
        {'moduleKey': 'candidate', 'mode': 'all', 'write': write_value},
    ])

    assert status == 200, f'write={write_value!r} 不应报错：HTTP {status} {body}'
    after = write_rows(role.role_code)
    assert len(after) == 1, (
        f'write={write_value!r} 时 WRITE 行被抹除：{len(before)} -> {len(after)} '
        f'（无意图的 payload 抹掉了管理员配置）'
    )
    assert after == before, f'WRITE 行被删后重建或actions 被改写：{before} -> {after}'
    assert body['data']['writeNormalized'] == ['candidate'], '未表达意图时应计入哨兵'
    got = next(m for m in body['data']['modules'] if m['moduleKey'] == 'candidate')
    assert got['write']['mode'] == 'all', '响应回读不应把写配置变成 none'
    assert got['write']['actions'] == ['edit']


# ============ 场景 4：显式 none → 真删（与上面构成本次修复的核心区分）============

def test_http_explicit_none_write_deletes_rule(admin_client, role):
    """payload 显式带 {mode:'none'} → WRITE 行应被删（管理员主动取消）。

    若这条不成立，说明守卫过宽，把管理员的取消操作也吞了 —— 同样是缺陷。
    """
    before = _seed_write(admin_client, role)
    assert len(before) == 1, f'删前 count 应为 1，实际 {len(before)}'

    status, body = _post(admin_client, role, [
        {'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'none'}},
    ])

    assert status == 200, f'HTTP {status} {body}'
    after = write_rows(role.role_code)
    assert len(after) == 0, f'显式 none 应删行：{len(before)} -> {len(after)}'
    got = next(m for m in body['data']['modules'] if m['moduleKey'] == 'candidate')
    assert got['write']['mode'] == 'none', '响应应回显 none'


def test_http_explicit_none_with_extra_keys_still_deletes(admin_client, role):
    """`{mode:'none', actions:[]}`（非空 dict + 显式 none）→ 仍应删行。

    守住"显式且非空"的边界：不能因为带了别的键就退化成"未表达意图"。
    """
    before = _seed_write(admin_client, role)
    assert len(before) == 1, f'删前 count 应为 1，实际 {len(before)}'

    status, body = _post(admin_client, role, [
        {'moduleKey': 'candidate', 'mode': 'all',
         'write': {'mode': 'none', 'actions': []}},
    ])

    assert status == 200, f'HTTP {status} {body}'
    after = write_rows(role.role_code)
    assert len(after) == 0, f'显式 none（带多余键）应删行：{len(before)} -> {len(after)}'


# ============ 场景 5：显式 all → 原地更新（id 不变）============

def test_http_explicit_write_updates_in_place(admin_client, role):
    """显式 {mode:'all',actions:[...]} → 原地更新，**id 不变**（审计不断链）。"""
    before = _seed_write(admin_client, role, actions=('edit',))
    assert len(before) == 1, f'删前 count 应为 1，实际 {len(before)}'
    before_id = before['candidate'][0]

    status, body = _post(admin_client, role, [
        {'moduleKey': 'candidate', 'mode': 'all',
         'write': {'mode': 'all', 'actions': ['edit', 'delete']}},
    ])

    assert status == 200, f'HTTP {status} {body}'
    after = write_rows(role.role_code)
    assert len(after) == 1, f'行数应保持 1：{len(before)} -> {len(after)}'
    assert after['candidate'][0] == before_id, (
        f'WRITE 行被删后重建（id {before_id} -> {after["candidate"][0]}）—— '
        f'这会切断审计链与列表页脚注'
    )
    assert after['candidate'][1] == ['edit', 'delete'], f'actions 未更新：{after}'
    got = next(m for m in body['data']['modules'] if m['moduleKey'] == 'candidate')
    assert got['write']['actions'] == ['edit', 'delete']


# ============ 场景 6：兼容式强校验边界（存量无 WRITE 行 + 缺键）============

def test_http_no_existing_write_rule_missing_key_is_noop(admin_client, role):
    """存量**无** WRITE 行 + 缺 write 键 → 不造行、哨兵 []、不报错。

    这是"兼容式强校验不打断存量首轮保存"的关键：新建角色首次保存不该被拦。
    """
    status, body = _post(admin_client, role, [{'moduleKey': 'candidate', 'mode': 'all'}])

    assert status == 200, f'存量首轮保存不应被拦：HTTP {status} {body}'
    assert write_rows(role.role_code) == {}, '不应凭空造出 WRITE 行'
    assert body['data']['writeNormalized'] == [], '无历史 WRITE 行时不应告警（否则哨兵变噪声）'


@pytest.mark.parametrize('write_value', [None, {}], ids=['null', 'empty-dict'])
def test_http_no_existing_write_rule_null_or_empty_is_noop(admin_client, role, write_value):
    """守卫收紧不能反过来把"新建角色首轮保存"堵死。

    与 test_http_no_existing_write_rule_missing_key_is_noop 配对：
    存量无 WRITE 行 + write:null/{} → 同样不造行、不报错、不告警。
    """
    status, body = _post(admin_client, role, [
        {'moduleKey': 'candidate', 'mode': 'all', 'write': write_value},
    ])

    assert status == 200, f'write={write_value!r} 时首轮保存被拦：HTTP {status} {body}'
    assert write_rows(role.role_code) == {}, '不应凭空造出 WRITE 行'
    assert body['data']['writeNormalized'] == [], '无历史 WRITE 行时不应告警'


# ============ 回归：未提交模块的行不能被删（差分核心）============

def test_http_untouched_module_row_survives(admin_client, role):
    """payload 只提交 candidate 时，position 的既有行必须完全不动。"""
    # 先给两个模块都配写范围
    status, body = _post(admin_client, role, [
        {'moduleKey': 'candidate', 'mode': 'all',
         'write': {'mode': 'all', 'actions': ['edit']}},
        {'moduleKey': 'position', 'mode': 'all',
         'write': {'mode': 'all', 'actions': ['edit']}},
    ])
    assert status == 200, f'HTTP {status} {body}'
    before = write_rows(role.role_code)
    assert len(before) == 2, f'删前应有 2 行，实际 {len(before)}'

    # 只提交 candidate，且显式取消它的写范围
    status, body = _post(admin_client, role, [
        {'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'none'}},
    ])
    assert status == 200, f'HTTP {status} {body}'

    after = write_rows(role.role_code)
    assert len(after) == 1, f'只应删candidate 一行：{len(before)} -> {len(after)}'
    assert 'position' in after, '未提交的 position 模块被连带删除'
    assert after['position'] == before['position'], 'position 行被改写'


# ============ 脏数据：非 dict 必须响亮失败 ============

def test_http_non_dict_write_rejected_400(admin_client, role):
    """write 为字符串是脏数据（非"未表达意图"）→ 必须 400 报错，绝不静默当 none。"""
    _seed_write(admin_client, role)

    status, body = _post(admin_client, role, [
        {'moduleKey': 'candidate', 'mode': 'all', 'write': 'all'},
    ])

    assert status == 400, f'非对象 write 应 400，实际 HTTP {status}'
    assert body.get('success') is False
    assert '对象' in body.get('message', ''), f'错误文案应说明必须是对象：{body}'
    # 双重断言：400 之后行必须原封不动（校验失败不得有副作用）
    assert len(write_rows(role.role_code)) == 1, '校验失败却改了数据'


# ============ 读配置不被写范围逻辑连带丢弃 ============

def test_http_read_config_survives_write_none(admin_client, role):
    """显式取消写范围时，读范围配置必须仍在（不能一起删掉）。"""
    before = _seed_write(admin_client, role)
    assert len(before) == 1

    status, body = _post(admin_client, role, [
        {'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'none'}},
    ])
    assert status == 200, f'HTTP {status} {body}'

    read_rows = DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role.role_code,
        level='ROW', entity='candidate',
    ).exclude(row_access='WRITE')
    assert read_rows.exists(), '读范围行被连带删除了'
    got = next(m for m in body['data']['modules'] if m['moduleKey'] == 'candidate')
    assert got['mode'] == 'all', '读配置应保留 mode=all'
