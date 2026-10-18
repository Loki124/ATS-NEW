"""Tests for V2 permission resource + template API endpoints."""
import pytest


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_resource_list_returns_correct_codes(auth_client):
    from apps.core.models_permission_v2 import PermissionResource
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test:menu:view',
        resource_name='T', resource_type='MENU', module='test',
    )
    resp = auth_client.get('/api/v1/permissions/resources/?module=test')
    assert resp.status_code == 200
    data = resp.json()
    items = data['data'] if isinstance(data, dict) and 'data' in data else data
    assert any(r['resourceCode'] == 'recruit:test:menu:view' for r in items)


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_resource_list_hides_disabled_by_default(auth_client):
    """缺省只出启用资源：停用项不得进入权限配置的可勾选候选。

    背景（2026-10-18 兵哥）：新增「资源状态」语义，停用 = 功能已下线。
    资源管理台要走 ?status=all 才能看到停用项（停用 ≠ 物理删除，须可审计），
    但权限配置类消费方保持「仅启用」的旧行为，不能因新增参数而行为漂移。
    """
    from apps.core.models_permission_v2 import PermissionResource
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test2:menu:view',
        resource_name='启用项', resource_type='MENU', module='test2', status=1,
    )
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test2:btn:delete',
        resource_name='停用项', resource_type='BUTTON', module='test2', status=0,
    )
    resp = auth_client.get('/api/v1/permissions/resources/?module=test2')
    assert resp.status_code == 200
    data = resp.json()
    items = data['data'] if isinstance(data, dict) and 'data' in data else data
    codes = {r['resourceCode'] for r in items}
    assert 'recruit:test2:menu:view' in codes
    assert 'recruit:test2:btn:delete' not in codes


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_resource_list_status_all_includes_disabled(auth_client):
    """?status=all → 启用 + 停用全见（资源管理台审计用）。"""
    from apps.core.models_permission_v2 import PermissionResource
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test3:menu:view',
        resource_name='启用项', resource_type='MENU', module='test3', status=1,
    )
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test3:btn:delete',
        resource_name='停用项', resource_type='BUTTON', module='test3', status=0,
    )
    resp = auth_client.get('/api/v1/permissions/resources/?module=test3&status=all')
    assert resp.status_code == 200
    data = resp.json()
    items = data['data'] if isinstance(data, dict) and 'data' in data else data
    codes = {r['resourceCode'] for r in items}
    assert codes == {'recruit:test3:menu:view', 'recruit:test3:btn:delete'}


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_resource_list_status_zero_returns_only_disabled(auth_client):
    """?status=0 → 仅停用。"""
    from apps.core.models_permission_v2 import PermissionResource
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test4:menu:view',
        resource_name='启用项', resource_type='MENU', module='test4', status=1,
    )
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test4:btn:delete',
        resource_name='停用项', resource_type='BUTTON', module='test4', status=0,
    )
    resp = auth_client.get('/api/v1/permissions/resources/?module=test4&status=0')
    assert resp.status_code == 200
    data = resp.json()
    items = data['data'] if isinstance(data, dict) and 'data' in data else data
    codes = {r['resourceCode'] for r in items}
    assert codes == {'recruit:test4:btn:delete'}


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_resource_list_rejects_illegal_status_fallback_to_enabled(auth_client):
    """非法 status 值退回「仅启用」，不得意外泄露停用资源。"""
    from apps.core.models_permission_v2 import PermissionResource
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test5:btn:delete',
        resource_name='停用项', resource_type='BUTTON', module='test5', status=0,
    )
    resp = auth_client.get('/api/v1/permissions/resources/?module=test5&status=whatever')
    assert resp.status_code == 200
    data = resp.json()
    items = data['data'] if isinstance(data, dict) and 'data' in data else data
    assert items == []


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_template_list(auth_client):
    from apps.core.models_permission_v2 import PermissionTemplate
    PermissionTemplate.objects.create(
        system_code='recruit',
        template_code='TMPL_TEST', template_name='T',
        is_system=1, permission_codes=['recruit:test:menu:view'],
    )
    resp = auth_client.get('/api/v1/permissions/templates/')
    assert resp.status_code == 200
    data = resp.json()
    items = data['data'] if isinstance(data, dict) and 'data' in data else data
    assert any(t['templateCode'] == 'TMPL_TEST' for t in items)