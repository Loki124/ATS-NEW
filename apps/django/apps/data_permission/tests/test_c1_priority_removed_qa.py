"""QA 独立验证：DataPermissionRule.priority 已彻底下掉（C1，零迁移）。

## 验证点

1. **模型层无 priority 字段**（静态断言，防"注释说删了但字段还在"）；
2. **makemigrations --check 无待生成迁移**（模型与迁移一致，不是漏迁);
3. **PATCH {"priority":5} 不 500**：历史客户端/外部脚本若仍带该键，
   必须被忽略（未知字段静默丢弃）而不是炸 500 —— 这是"下掉死字段"
   不影响存量调用的关键；
4. **PATCH 后库里依然没有该列**（不是"接受了但存到别处"）。
"""
import pytest
from django.test import Client

from apps.core.models import User
from apps.data_permission.models import DataPermissionRule

LIST_URL = '/api/v1/data-permissions/'


def _token(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    return 'Bearer ' + str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def super_admin(db):
    return User.objects.create(username='qa_priority_admin', is_superuser=True, is_active=True)


@pytest.fixture
def rule(db, super_admin):
    return DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value='QA_PRIORITY_ROLE',
        level='ROW', entity='candidate', scope_type='ALL', row_access='WRITE',
        status=1, created_by=super_admin.pk,
    )


def _client_for(user):
    c = Client()
    c._qa_token = _token(user)
    return c


# ============ 1. 模型层无 priority ============

def test_model_has_no_priority_field():
    """静态断言：DataPermissionRule 不得再有 priority 字段。

    设计文档 §0.2 D1：旧字段"大者优先"从未被任何读取方消费，是死字段。
    若它还在，本次"下掉"就是假的。
    """
    names = {f.name for f in DataPermissionRule._meta.get_fields()}
    assert 'priority' not in names, (
        f'DataPermissionRule 仍存在 priority 字段：{sorted(names)}'
    )


def test_priority_removed_by_migration_and_never_readded():
    """迁移历史必须包含"删除 priority"的那一笔，且之后不得再加回。

    历史里提及 priority 是**正常**的：0001_initial 创建它、
    0007_remove_... 删除它。QA 第一版一刀切地禁所有提及，误报。
    真正要禁的是：删除迁移之后的迁移又把 priority 加回来。
    """
    import io
    import os

    mig_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '..', 'data_permission', 'migrations',
    )
    files = [fn for fn in sorted(os.listdir(mig_dir))
             if fn.endswith('.py') and fn != '__init__.py']

    removal_idx = None
    for i, fn in enumerate(files):
        if 'remove' in fn and 'priority' in fn:
            removal_idx = i
            break
    assert removal_idx is not None, (
        f'未找到删除 priority 的迁移文件（应有形如 '
        f'000X_remove_datapermissionrule_priority.py）：{files}'
    )

    later = files[removal_idx + 1:]
    readded = []
    for fn in later:
        text = io.open(os.path.join(mig_dir, fn), encoding='utf-8').read()
        # 只关心"新增/修改字段"类引用，注释里提到不算
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if 'priority' in stripped and (
                'name=' in stripped or 'AddField' in stripped or 'field=' in stripped
            ):
                readded.append(f'{fn}: {stripped[:80]}')
    assert not readded, f'删除迁移之后又把 priority 加回：{readded}'


# ============ 2. 无待生成迁移 ============

def test_makemigrations_check_clean():
    """`makemigrations --check` 必须无待生成迁移。

    若模型改了却没生成迁移（或迁多了），这里会非零退出 ——
    防止"代码说删了、数据库结构没同步"的分裂状态。
    """
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, 'manage.py', 'makemigrations', '--check', '--dry-run'],
        capture_output=True, text=True, cwd=os_cwd(),
    )
    assert proc.returncode == 0, (
        f'存在待生成的迁移（模型与迁移不一致）：\n'
        f'stdout={proc.stdout[-800:]}\nstderr={proc.stderr[-800:]}'
    )


def os_cwd():
    """manage.py 位于 apps/django/（不是 app 目录）—— QA 第一版路径搞错，
    子进程报 "can't open file .../apps/data_permission/manage.py"。
    """
    import os
    # 本文件在 <repo>/apps/django/apps/data_permission/tests/ 下，
    # 上溯四级才到 manage.py 所在的 apps/django/（QA 第一版只上溯三级，
    # 落在 apps/ 上报 "can't open file .../apps/manage.py"）。
    here = os.path.abspath(__file__)
    for _ in range(4):
        here = os.path.dirname(here)
    return here


# ============ 3. PATCH 带 priority 不 500 ============

def test_patch_with_priority_key_is_ignored_not_500(super_admin, rule):
    """PATCH {"priority":5} → 不得 500，且不得落库（未知字段应被忽略）。

    这是"下掉死字段"的兼容性关键：历史客户端/外部脚本若仍带该键，
    必须静默忽略。若 DRF 序列化器把它当未知字段报 400 也算失败
    （要求是"被忽略"而不是"被拒绝"）—— 但不允许 500。
    """
    import json

    c = _client_for(super_admin)
    url = f'{LIST_URL}{rule.pk}/'
    resp = c.patch(
        url, data=json.dumps({'priority': 5}),
        content_type='application/json',
        HTTP_AUTHORIZATION=c._qa_token,
    )

    assert resp.status_code != 500, (
        f'PATCH 带 priority 触发了 500（未知字段未被容错）：{resp.status_code}'
    )
    # 无论 200/400，库里都不该冒出 priority 相关数据
    rule.refresh_from_db()
    assert not hasattr(rule, 'priority'), '对象上出现了 priority 属性'


def test_patch_priority_does_not_change_other_fields(super_admin, rule):
    """PATCH 只带 priority 时，其他字段不得被连带改动。"""
    import json

    before_scope = rule.scope_type
    before_access = rule.row_access

    c = _client_for(super_admin)
    resp = c.patch(
        f'{LIST_URL}{rule.pk}/', data=json.dumps({'priority': 5}),
        content_type='application/json',
        HTTP_AUTHORIZATION=c._qa_token,
    )
    assert resp.status_code != 500, f'HTTP {resp.status_code}'

    rule.refresh_from_db()
    assert rule.scope_type == before_scope, 'priority PATCH 连带改写了 scope_type'
    assert rule.row_access == before_access, 'priority PATCH 连带改写了 row_access'


# ============ 4. 写接口不产出 priority ============

def test_rule_create_response_has_no_priority(super_admin, role_v2):
    """规则写接口的响应体不得再含 priority 键（前端契约已不需要）。"""
    import json

    c = _client_for(super_admin)
    resp = c.post(
        LIST_URL,
        data=json.dumps({
            'dimension_type': 'ROLE', 'dimension_value': role_v2.role_code,
            'level': 'ROW', 'entity': 'candidate', 'scope_type': 'ALL',
            'row_access': 'WRITE',
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=c._qa_token,
    )
    assert resp.status_code in (200, 201), f'HTTP {resp.status_code}: {resp.content[:300]}'
    body = resp.json()
    blob = json.dumps(body, ensure_ascii=False)
    assert 'priority' not in blob, f'响应体仍含 priority：{blob[:400]}'


@pytest.fixture
def role_v2(db):
    from apps.core.models_permission_v2 import RoleV2
    return RoleV2.objects.create(
        system_code='recruit', role_code='QA_PRIO_ROLE',
        role_name='QA priority 角色', status=1,
    )
