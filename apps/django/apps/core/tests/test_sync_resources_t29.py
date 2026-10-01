"""E2E for T29 sync-resources action — 角色资源勾选同步.

Root cause (T29): RoleSerializer.permission_codes 是 SerializerMethodField (read-only),
PUT /roles/{id}/ 时该字段被 DRF 静默丢弃, 用户勾选的 checkbox 数据丢失.

修复: 新增 POST /roles/{id}/sync-resources/ action 显式整组替换 role_permission.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError, ProgrammingError
from rest_framework.test import APIClient


User = get_user_model()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='syncadmin', password='x',
        is_staff=True, is_superuser=True,
    )


@pytest.fixture
def seed_templates(db):
    """R7 (2026-08-03 寇豆码): sync_resources_t29 测试依赖 TMPL_ADMIN 模板存在.

    conftest.py (fixtures_common._ensure_v2_schema) 故意不 seed permission_resources /
    permission_templates (会破坏 test_bootstrap 假设空 DB). 各 sync_resources 用例
    必须显式 seed 才能 clone-from-template 成功. empty_array_clears 在用例体里手动
    call_command, 这两条 (persists_codes / rejects_invalid_codes) 通过本 fixture 统一处理.
    """
    from django.core.management import call_command
    call_command('seed_v2_init', verbosity=0)
    return None


def _v2_schema_ready():
    """探测 V2 roles + role_permission 表是否已有 V2-only 列 (T17-applied).
    如果未应用, 表是 V1 schema, 跳过这些测试.
    """
    try:
        from django.db import connection
        with connection.cursor() as c:
            # roles 表 V2 列: role_code / role_name / template_code / default_data_scope_type
            if 'sqlite' in connection.vendor:
                c.execute("PRAGMA table_info(roles)")
            else:
                c.execute("DESCRIBE roles")
            roles_cols = {row[1] for row in c.fetchall()}

            if 'sqlite' in connection.vendor:
                c.execute("PRAGMA table_info(role_permission)")
            else:
                c.execute("DESCRIBE role_permission")
            rp_cols = {row[1] for row in c.fetchall()}
        # 必须 V2 列都已存在
        return {'role_code'}.issubset(roles_cols) and {'resource_code'}.issubset(rp_cols)
    except (OperationalError, ProgrammingError):  # 测试代码: 列缺失返 False (probe 函数, 不应让测试 setup 崩)
        return False


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_sync_resources_persists_codes(admin, seed_templates):
    """POST sync-resources → role_permission 表实际入库, 重读 ROLE 看到 codes."""
    if not _v2_schema_ready():
        pytest.skip('needs T17 v2 schema (role_permission.resource_code column)')
    client = APIClient()
    client.force_authenticate(user=admin)

    # 1. 新建 role (clone-from-template)
    res = client.post('/api/v1/roles/clone-from-template/', {
        'templateCode': 'TMPL_ADMIN',
        'roleCode': 'SYNC_TEST_ROLE',
        'roleName': '同步测试角色',
    }, format='json')
    assert res.status_code in (200, 201), res.content[:300]

    # 2. 创建 2 个测试资源
    from apps.core.models_permission_v2 import PermissionResource, RoleV2, RolePermissionV2
    PermissionResource.objects.get_or_create(
        resource_code='test:sync:res1',
        defaults={'system_code': 'recruit', 'resource_name': 'S1',
                  'resource_type': 'BUTTON', 'module': 'test', 'status': 1},
    )
    PermissionResource.objects.get_or_create(
        resource_code='test:sync:res2',
        defaults={'system_code': 'recruit', 'resource_name': 'S2',
                  'resource_type': 'BUTTON', 'module': 'test', 'status': 1},
    )

    # 3. 找到新建的 role id
    role = RoleV2.objects.get(role_code='SYNC_TEST_ROLE', system_code='recruit')

    # 4. POST sync-resources
    res = client.post(
        f'/api/v1/roles/{role.id}/sync-resources/',
        {'resourceCodes': ['test:sync:res1', 'test:sync:res2']},
        format='json',
    )
    assert res.status_code == 200, res.content[:300]

    # 5. 验证: DB 里真有 2 条 role_permission 记录
    rows = RolePermissionV2.objects.filter(
        role_code='SYNC_TEST_ROLE', system_code='recruit',
    ).values_list('resource_code', flat=True)
    assert set(rows) == {'test:sync:res1', 'test:sync:res2'}

    # 6. 第二次 sync 改成只保留 res1, 验证整组替换 (不是 append)
    res = client.post(
        f'/api/v1/roles/{role.id}/sync-resources/',
        {'resourceCodes': ['test:sync:res1']},
        format='json',
    )
    assert res.status_code == 200
    rows = list(RolePermissionV2.objects.filter(
        role_code='SYNC_TEST_ROLE', system_code='recruit',
    ).values_list('resource_code', flat=True))
    assert rows == ['test:sync:res1'], f'应只剩 res1, 实际: {rows}'


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_sync_resources_rejects_invalid_codes(admin, seed_templates):
    """无效 resource_code 应返回 400 而非 crash."""
    if not _v2_schema_ready():
        pytest.skip('needs T17 v2 schema (role_permission.resource_code column)')
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post('/api/v1/roles/clone-from-template/', {
        'templateCode': 'TMPL_ADMIN',
        'roleCode': 'REJECT_TEST_ROLE',
        'roleName': '拒绝测试',
    }, format='json')
    assert res.status_code in (200, 201)

    from apps.core.models_permission_v2 import RoleV2
    role = RoleV2.objects.get(role_code='REJECT_TEST_ROLE', system_code='recruit')

    res = client.post(
        f'/api/v1/roles/{role.id}/sync-resources/',
        {'resourceCodes': ['non_existent_resource_code_xyz']},
        format='json',
    )
    assert res.status_code == 400
    assert 'invalid' in str(res.content).lower() or '无效' in str(res.content)


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_sync_resources_empty_array_clears(admin):
    """传空数组应清除该 role 所有 role_permission 记录."""
    if not _v2_schema_ready():
        pytest.skip('needs T17 v2 schema (role_permission.resource_code column)')
    client = APIClient()
    client.force_authenticate(user=admin)

    from apps.core.models_permission_v2 import RoleV2, RolePermissionV2, PermissionResource
    PermissionResource.objects.get_or_create(
        resource_code='test:clear:res',
        defaults={'system_code': 'recruit', 'resource_name': 'C1',
                  'resource_type': 'BUTTON', 'module': 'test', 'status': 1},
    )

    from django.core.management import call_command
    call_command('seed_v2_init', verbosity=0)

    res = client.post('/api/v1/roles/clone-from-template/', {
        'templateCode': 'TMPL_ADMIN',
        'roleCode': 'CLEAR_TEST_ROLE',
        'roleName': '清空测试',
    }, format='json')
    assert res.status_code in (200, 201)
    role = RoleV2.objects.get(role_code='CLEAR_TEST_ROLE', system_code='recruit')

    # 先加一条
    client.post(
        f'/api/v1/roles/{role.id}/sync-resources/',
        {'resourceCodes': ['test:clear:res']},
        format='json',
    )
    assert RolePermissionV2.objects.filter(role_code='CLEAR_TEST_ROLE').count() == 1

    # 再清空
    res = client.post(
        f'/api/v1/roles/{role.id}/sync-resources/',
        {'resourceCodes': []},
        format='json',
    )
    assert res.status_code == 200
    assert RolePermissionV2.objects.filter(role_code='CLEAR_TEST_ROLE').count() == 0


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_sync_resources_route_exists_no_crash(db):
    """Schema-agnostic smoke: sync-resources 路由必须存在 (404 OK for fake pk).
    T17 前后都应通过 — 验证 wiring 正确.
    """
    from rest_framework.test import APIClient
    user = User.objects.create_user(username='routetest', password='x', is_superuser=True)
    client = APIClient()
    client.force_authenticate(user=user)
    res = client.post('/api/v1/roles/00000000-0000-0000-0000-000000000000/sync-resources/',
                      {'resourceCodes': ['test:fake']}, format='json')
    # 期望 404 (role 不存在) 或 400 (resourceCode 无效), 不是 500/401/NotImplemented
    assert res.status_code in (400, 404), f'route broken: {res.status_code} {res.content[:200]}'
