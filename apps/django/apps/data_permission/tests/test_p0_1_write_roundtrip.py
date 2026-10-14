"""P0-1 回归：写范围保存往返 + 缺 write 不被抹除（2026-10-14 T02）。

对应 docs/ARCH_数据权限P0止血_系统设计.md §1.2.4。

## 为什么这些断言必须查库、不能只看接口 200

历史 bug 的形态就是「接口返回 200，但配置没了」。任何"断言 200 / 断言提示成功"
的用例在旧代码上**恒绿**，属于设计文档 §0.3 DR-01 所说的"假绿"。
故本文件所有用例一律直接断言 `DataPermissionRule` 的行数 / 字段值。

## 覆盖的两种存量情形（兼容式强校验不打断存量保存）

| 情形 | 期望 |
|---|---|
| 存量**有** WRITE 规则 + payload 缺 write 键 | WRITE 行**原样保留** + 响应 writeNormalized 命中该模块（可观测哨兵） |
| 存量**无** WRITE 规则 + payload 缺 write 键 | 不报错、不产生 WRITE 行、writeNormalized **不**命中（补默认值属正常，不告警） |
"""
import pytest

from apps.core.models_permission_v2 import RoleV2
from apps.data_permission.models import DataPermissionRule
from apps.data_permission.role_scope_api import build_modules_response, upsert_modules

ROLE_CODE = 'P0_1_WRITE_ROLE'


@pytest.fixture
def role(db):
    return RoleV2.objects.create(
        system_code='recruit', role_code=ROLE_CODE, role_name='P0-1 写范围回归', status=1,
    )


@pytest.fixture
def admin_user(db):
    from apps.core.models import User
    return User.objects.create(username='p0_1_admin', is_superuser=True, is_active=True)


def write_rules(role_code: str):
    """该角色全部 WRITE 行（按 entity 归组）。"""
    out = {}
    for r in DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role_code,
        level='ROW', row_access='WRITE',
    ):
        out[r.entity] = r
    return out


def read_rules(role_code: str):
    out = {}
    for r in DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role_code, level='ROW',
    ).exclude(row_access='WRITE'):
        out[r.entity] = r
    return out


# ============ 用例 1：写范围往返（正常路径） ============

def test_write_roundtrip_all_mode(role, admin_user):
    """提交 write.mode=all + actions=['edit'] → WRITE 行落库且 actions 正确。"""
    modules = [{'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'all', 'actions': ['edit']}}]

    data = upsert_modules(role, modules, admin_user)

    rows = write_rules(ROLE_CODE)
    assert rows, 'WRITE 行未落库'
    assert rows['candidate'].scope_type == 'ALL'
    assert list(rows['candidate'].actions) == ['edit']
    # 响应回读一致（前端用返回值覆盖 draft，漂移会直接显示在 UI 上）
    got = next(m for m in data['modules'] if m['moduleKey'] == 'candidate')
    assert got['write']['mode'] == 'all'
    assert got['write']['actions'] == ['edit']
    assert data['writeNormalized'] == []


# ============ 用例 2：P0-1 核心回归 —— 缺 write 键不抹除 ============

def test_write_not_wiped_when_field_absent(role, admin_user):
    """payload **缺** write 键时，原 WRITE 行必须原样保留，且哨兵命中。

    这是 P0-1 的核心回归用例：旧实现「先删后建」会把WRITE 行删掉不重建。
    步骤严格照DR-01 的"先证明有数据、再证明未被破坏"两步法，
    避免断言恒真（若无WRITE 行，"仍存在" 这句就是废话）。
    """
    # --- 先 seed 出真实的 WRITE 行 ---
    upsert_modules(
        role,
        [{'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'all', 'actions': ['edit']}}],
        admin_user,
    )
    seeded = write_rules(ROLE_CODE)
    assert seeded['candidate'].scope_type == 'ALL', 'seed 失败，测试无鉴别力'
    seeded_id = seeded['candidate'].id

    # --- 再提交缺 write 键的 payload（模拟前端序列化回归）---
    data = upsert_modules(
        role, [{'moduleKey': 'candidate', 'mode': 'all'}], admin_user,
    )

    after = write_rules(ROLE_CODE)
    assert 'candidate' in after, 'WRITE 行被抹除了 —— P0-1 未修复'
    assert after['candidate'].scope_type == 'ALL', 'scope_type 被改写'
    assert list(after['candidate'].actions) == ['edit'], 'actions 被改写'
    # 原地更新而非删了重建：id 不变（审计链不断）
    assert after['candidate'].id == seeded_id
    # 哨兵：可观测，防复发
    assert data['writeNormalized'] == ['candidate']
    # 响应回读仍是原配置（前端不会被"配置消失"覆盖）
    got = next(m for m in data['modules'] if m['moduleKey'] == 'candidate')
    assert got['write']['mode'] == 'all'
    assert got['write']['actions'] == ['edit']


def test_write_normalized_absent_for_role_without_write_rules(role, admin_user):
    """存量**无** WRITE 规则 + 缺 write 键 → 补默认值属正常，**不**进哨兵。

    这是"兼容式强校验不打断存量首轮保存"的另一半：新建角色首次保存时前端
    无论带不带 write 都不该告警，否则告警会变成噪声而被忽略。
    """
    data = upsert_modules(
        role, [{'moduleKey': 'candidate', 'mode': 'all'}], admin_user,
    )

    assert write_rules(ROLE_CODE) == {}, '缺 write 键不应凭空造出 WRITE 行'
    assert data['writeNormalized'] == [], '无历史 WRITE 行时不应告警'


def test_explicit_none_write_deletes_rule(role, admin_user):
    """**显式** write.mode='none' = 管理员主动取消写范围 → 该行必须被删。

    与上一条用例构成本次修复的核心区分：缺键=保留，显式 none=删除。
    若把缺键也当 none 处理，管理员将永远无法取消写范围（本用例会红）。
    """
    upsert_modules(
        role,
        [{'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'all', 'actions': ['edit']}}],
        admin_user,
    )
    assert write_rules(ROLE_CODE), 'seed 失败'

    data = upsert_modules(
        role,
        [{'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'none', 'actions': []}}],
        admin_user,
    )

    assert write_rules(ROLE_CODE) == {}, '显式 none 未删除 WRITE 行'
    # 显式提交是管理员的明确意图，不属"漏传"，不进哨兵
    assert data['writeNormalized'] == []
    got = next(m for m in data['modules'] if m['moduleKey'] == 'candidate')
    assert got['write']['mode'] == 'none'


# ============ 用例 3：读配置不被连带丢弃 ============

def test_read_config_preserved_when_write_absent(role, admin_user):
    """缺 write 键时，读范围的条件组必须完整落库（不被 write 分支牵连）。"""
    groups = [{
        'expr': '',
        'conditions': [{
            'kind': 'dimension', 'dimension': 'department', 'operator': 'IN',
            'values': [{'id': 'D1', 'label': '华东大区'}],
        }],
    }]
    upsert_modules(
        role,
        [{'moduleKey': 'candidate', 'mode': 'all',
          'write': {'mode': 'all', 'actions': ['edit']}}],
        admin_user,
    )

    data = upsert_modules(
        role, [{'moduleKey': 'candidate', 'mode': 'scope', 'expr': '', 'groups': groups}],
        admin_user,
    )

    read_row = read_rules(ROLE_CODE)['candidate']
    assert read_row.scope_type == 'CUSTOM'
    assert len(read_row.scope_payload['groups']) == 1
    assert read_row.scope_payload['groups'][0]['conditions'][0]['dimension'] == 'department'
    got = next(m for m in data['modules'] if m['moduleKey'] == 'candidate')
    assert got['mode'] == 'scope'
    assert len(got['groups']) == 1


# ============ 用例 4：写范围自身的强校验不放宽 ============

def test_missing_write_rejected_when_actions_empty(role, admin_user):
    """write.mode='all' 但 actions=[] → 400（复用 _validate_write_block）。

    兼容式强校验只对"**缺键**"宽容；一旦显式提交了 write，内容仍必须严格校验 ——
    否则"配了范围却没勾动作"这种歧义配置会被静默放行。
    """
    from apps.data_permission.role_scope_api import validate_modules
    reason = validate_modules([
        {'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'all', 'actions': []}},
    ])
    assert reason, '显式 write.mode=all 但 actions 为空必须被拒'
    assert 'actions' in reason


def test_invalid_write_mode_rejected(role, admin_user):
    """write.mode 非法值 → 校验失败（不得当成 none 静默吞掉）。"""
    from apps.data_permission.role_scope_api import validate_modules
    reason = validate_modules([
        {'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'bogus', 'actions': ['edit']}},
    ])
    assert reason
    assert 'write.mode' in reason


# ============ 用例 5：差分重建 —— 未提交的模块不被删 ============

def test_unrelated_module_rows_untouched(role, admin_user):
    """提交 1 个模块，另 2 个模块的行必须**完全不动**（差分重建的核心）。

    旧「全删后建」实现下这条会红：未被 payload 提及的模块行会被 DELETE 掉，
    读回时 build_modules_response 回落成 mode='all'（静默放宽数据可见范围）。
    """
    for mk in ('demand', 'process', 'position'):
        upsert_modules(
            role,
            [{'moduleKey': mk, 'mode': 'all', 'write': {'mode': 'all', 'actions': ['edit']}}],
            admin_user,
        )
    before = {
        mk: (read_rules(ROLE_CODE)[mk].id, read_rules(ROLE_CODE)[mk].scope_type)
        for mk in ('demand', 'process', 'position')
    }
    before_write = {mk: write_rules(ROLE_CODE)[mk].id for mk in ('demand', 'process', 'position')}
    assert before, 'seed 失败，测试无鉴别力'

    # 只提交 candidate 一个模块
    data = upsert_modules(
        role,
        [{'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'all', 'actions': ['edit']}}],
        admin_user,
    )

    after = {
        mk: (read_rules(ROLE_CODE)[mk].id, read_rules(ROLE_CODE)[mk].scope_type)
        for mk in ('demand', 'process', 'position')
    }
    assert after == before, '未提交的模块读行被改动'
    assert {mk: write_rules(ROLE_CODE)[mk].id for mk in ('demand', 'process', 'position')} == before_write
    # 响应里这 3 个模块仍是原配置（不是回落成 all）
    got = {m['moduleKey']: m for m in data['modules']}
    for mk in ('demand', 'process', 'position'):
        assert got[mk]['write']['actions'] == ['edit'], f'{mk} 写范围被回落'


# ============ 用例 6：原地更新保留 id / created_at ============

def test_existing_rule_updated_in_place_not_recreated(role, admin_user):
    """重复保存同一模块 → 规则行 id 不变（审计链、列表脚注不断链）。"""
    upsert_modules(
        role,
        [{'moduleKey': 'candidate', 'mode': 'all', 'write': {'mode': 'all', 'actions': ['edit']}}],
        admin_user,
    )
    first = read_rules(ROLE_CODE)['candidate'].id
    first_write = write_rules(ROLE_CODE)['candidate'].id

    upsert_modules(
        role,
        [{'moduleKey': 'candidate', 'mode': 'none', 'write': {'mode': 'all', 'actions': ['transition']}}],
        admin_user,
    )

    assert read_rules(ROLE_CODE)['candidate'].id == first, '读行被删了重建（应原地更新）'
    assert read_rules(ROLE_CODE)['candidate'].scope_type == 'NONE', '读范围未更新'
    assert write_rules(ROLE_CODE)['candidate'].id == first_write, '写行被删了重建（应原地更新）'
    assert list(write_rules(ROLE_CODE)['candidate'].actions) == ['transition'], 'actions 未更新'


# ============ 用例 7：响应契约 ============

def test_build_modules_response_always_has_write_normalized(role, admin_user):
    """读接口响应恒含 writeNormalized 键（正常为 []）—— 前端可无脑读。"""
    data = build_modules_response(role)
    assert 'writeNormalized' in data
    assert data['writeNormalized'] == []
    assert len(data['modules']) == 5, '5 模块必须齐套'