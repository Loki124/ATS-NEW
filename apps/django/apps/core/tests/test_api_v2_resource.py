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