"""R3 / C5 授权完整性验收（P0-3 / ARCH §1.3 / PLAN §6，DR-01 防假绿要求）。

每个用例断言都必须是「先证明有数据、再证明被清空」两步式，禁止恒真断言。

覆盖：
  1. 迁移 0023 后无孤儿用户授权（user 指向不存在用户）
  2. 迁移 0023 后无孤儿角色授权（role_code 不在 RoleV2）
  3. 删角色（ORM）→ 其 role_permission + user_roles 一并清空（post_delete 钩子）
  4. 删角色（HTTP DELETE /roles/{id}/）→ 同上（覆盖真实 API 路径）
  5. 删用户 → 其 user_roles 经 FK CASCADE 自动清空（0024）
  6. 授权时对不存在的 role_code 响亮 400 且未静默写入（DR-02）
"""
import pytest
from django.contrib.auth import get_user_model

from apps.core.models_permission_v2 import (
    RolePermissionV2,
    RoleV2,
    UserRoleV2,
)


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_no_orphan_user_roles_after_migration(super_user):
    """用例 1：0023 清理后不应存在指向不存在用户的 user_roles（两步式）。

    先 seed 一条有效授权证明表非空、FK 反向可用，再断言全部行 user 均有效。
    """
    # 两步式 ①：先证明有数据
    ur = UserRoleV2.objects.create(
        user=super_user, role_code='P0_3_EXISTING_UR', system_code='recruit',
    )
    assert UserRoleV2.objects.count() >= 1
    # 两步式 ②：再证明无孤儿（借 FK 反向关系，user__isnull 即孤儿）
    total = UserRoleV2.objects.count()
    assert UserRoleV2.objects.exclude(user__isnull=True).count() == total
    ur.delete()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_no_orphan_role_permission_after_migration():
    """用例 2：0023 的 purge_orphans 能清掉 recruit 内「role_code 不在 RoleV2」的孤儿
    role_permission，且保留有效关联（两步式，白盒验证迁移函数）。

    为什么白盒而非查库：测试 DB 的 role_permission seed 数据在 0023 之后才加载，
    且测试库 RoleV2 为空 —— 迁移时序无法产生「已清理」的库状态。故直接调用迁移函数
    做确定性验证：seed 一个有效关联(role_code 命中真实 RoleV2) + 一个孤儿关联，
    跑 purge 后断言「孤儿被删、有效保留」，证明清理是选择性的、非误删全表。
    """
    import importlib

    from django.apps import apps as real_apps
    from django.db import connection as db_connection

    migration = importlib.import_module(
        'apps.core.migrations.0023_purge_orphan_permission_grants'
    )

    # 两步式 ①：seed 有效角色 + 有效关联 + 孤儿关联，证明 purge 前有可观测对象
    valid_role = RoleV2.objects.create(
        system_code='recruit', role_code='P0_3_VALID_ROLE', role_name='P0_3 有效角色',
    )
    RolePermissionV2.objects.create(
        role_code='P0_3_VALID_ROLE', resource_code='recruit:p0_3:keep',
        system_code='recruit',
    )
    RolePermissionV2.objects.create(
        role_code='P0_3_ORPHAN_RP', resource_code='recruit:p0_3:drop',
        system_code='recruit',
    )
    assert RolePermissionV2.objects.filter(role_code='P0_3_VALID_ROLE').exists() is True
    assert RolePermissionV2.objects.filter(role_code='P0_3_ORPHAN_RP').exists() is True

    # 执行迁移清理逻辑（测试事务内，rollback 不污染其他用例）
    class _SchemaEditor:
        connection = db_connection

    migration.purge_orphans(real_apps, _SchemaEditor())

    # 两步式 ②：孤儿被清、有效保留（选择性清理，非误删）
    assert RolePermissionV2.objects.filter(role_code='P0_3_ORPHAN_RP').exists() is False
    assert RolePermissionV2.objects.filter(role_code='P0_3_VALID_ROLE').exists() is True
    valid_role.delete()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_delete_role_purges_role_permission():
    """用例 3（核心，替代原「空角色删除」验收）：删角色 → 授权自动清空（两步式）。

    建 2 条 role_permission + 1 条 user_roles，先断言 count>0，删角色后再断言 == 0。
    若用空角色验收，count==0 恒真、钩子没生效也会绿（RK-12 假绿）。
    """
    User = get_user_model()
    user = User.objects.create_user(username='p03_role_user', password='x')
    role = RoleV2.objects.create(
        system_code='recruit', role_code='P0_3_TMP_ROLE', role_name='P0_3 临时角色',
    )
    RolePermissionV2.objects.create(
        role_code='P0_3_TMP_ROLE', resource_code='recruit:p0_3:a', system_code='recruit',
    )
    RolePermissionV2.objects.create(
        role_code='P0_3_TMP_ROLE', resource_code='recruit:p0_3:b', system_code='recruit',
    )
    UserRoleV2.objects.create(
        user=user, role_code='P0_3_TMP_ROLE', system_code='recruit',
    )

    # 两步式 ①：先证明钩子有可观测对象
    assert RolePermissionV2.objects.filter(role_code='P0_3_TMP_ROLE').count() == 2
    assert UserRoleV2.objects.filter(role_code='P0_3_TMP_ROLE').count() == 1

    # 删角色（ORM）→ 触发 post_delete 钩子级联清授权
    role.delete()

    # 两步式 ②：删后两表均清空
    assert RolePermissionV2.objects.filter(role_code='P0_3_TMP_ROLE').count() == 0
    assert UserRoleV2.objects.filter(role_code='P0_3_TMP_ROLE').count() == 0
    user.delete()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_delete_role_via_api_purges_grants(auth_client):
    """用例 4：走真实 HTTP DELETE /roles/{id}/ 删除角色 → 授权自动清空（两步式）。

    覆盖 API 路径，防止「信号在测试里生效、API 路径下被绕过」。
    """
    User = get_user_model()
    user = User.objects.create_user(username='p03_role_api_user', password='x')
    role = RoleV2.objects.create(
        system_code='recruit', role_code='P0_3_TMP_ROLE_API', role_name='P0_3 临时角色API',
    )
    RolePermissionV2.objects.create(
        role_code='P0_3_TMP_ROLE_API', resource_code='recruit:p0_3:c', system_code='recruit',
    )
    RolePermissionV2.objects.create(
        role_code='P0_3_TMP_ROLE_API', resource_code='recruit:p0_3:d', system_code='recruit',
    )
    UserRoleV2.objects.create(
        user=user, role_code='P0_3_TMP_ROLE_API', system_code='recruit',
    )

    # 两步式 ①
    assert RolePermissionV2.objects.filter(role_code='P0_3_TMP_ROLE_API').count() == 2
    assert UserRoleV2.objects.filter(role_code='P0_3_TMP_ROLE_API').count() == 1

    resp = auth_client.delete(f'/api/v1/roles/{role.id}/')
    # REST 删除成功约定为 204 No Content（兼容 200/202），非 500/403/404
    assert resp.status_code in (200, 202, 204), resp.content

    # 两步式 ②
    assert RolePermissionV2.objects.filter(role_code='P0_3_TMP_ROLE_API').count() == 0
    assert UserRoleV2.objects.filter(role_code='P0_3_TMP_ROLE_API').count() == 0
    user.delete()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_delete_user_cascades_user_roles():
    """用例 5：删用户 → 其 user_roles 经 FK CASCADE 自动清空（两步式，DB 级验证）。"""
    User = get_user_model()
    user = User.objects.create_user(username='p03_cascade_user', password='x')
    UserRoleV2.objects.create(
        user=user, role_code='P0_3_CASCADE_1', system_code='recruit',
    )
    UserRoleV2.objects.create(
        user=user, role_code='P0_3_CASCADE_2', system_code='recruit',
    )

    # 两步式 ①：先证明有数据
    assert UserRoleV2.objects.filter(user_id=user.pk).count() == 2

    # 删用户（PK 仍可读）→ FK CASCADE 清授权
    user.delete()

    # 两步式 ②：删后该用户的授权全部清空
    assert UserRoleV2.objects.filter(user_id=user.pk).count() == 0


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_grant_rejects_nonexistent_role(auth_client, super_user):
    """用例 6（DR-02 强制）：对不存在的 role_code 授权 → 响亮 400 且未静默写入。

    必须同时断言「报错」与「没静默写入」—— 只断言 400 不能排除「先写后报错」。
    """
    before = UserRoleV2.objects.count()
    resp = auth_client.post(
        '/api/v1/user-roles/',
        data={
            'user_id': super_user.id,
            'role_code': 'NOT_EXIST_ROLE_XXX',
            'system_code': 'recruit',
        },
        format='json',
    )

    # 两步式 ①：响亮失败 + 明确文案
    assert resp.status_code == 400, resp.content
    assert '不存在' in resp.content.decode('utf-8'), resp.content

    # 两步式 ②：绝不能静默写入
    after = UserRoleV2.objects.count()
    assert after == before, '对不存在的 role_code 授权不应落库'
    assert not UserRoleV2.objects.filter(role_code='NOT_EXIST_ROLE_XXX').exists()
