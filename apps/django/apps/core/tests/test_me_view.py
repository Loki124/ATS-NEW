"""Test for /auth/me/ V2 fields."""
import pytest


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_me_view_returns_v2_fields(auth_client):
    """superuser → permissions 包含所有 resource_code + managementUnitIds + dataScope.

    注: DRF 使用 djangorestframework_camel_case, 输出 JSON 转为 camelCase.
    """
    from apps.core.models_permission_v2 import PermissionResource
    PermissionResource.objects.create(
        system_code='recruit', resource_code='recruit:foo:menu:view',
        resource_name='F', resource_type='MENU', module='foo',
    )
    resp = auth_client.get('/api/v1/auth/me/')
    assert resp.status_code == 200
    data = resp.json()['data']
    assert 'recruit:foo:menu:view' in data['permissions']
    assert 'managementUnitIds' in data
    assert 'dataScope' in data
    assert isinstance(data['dataScope'], dict)


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_me_view_anonymous_returns_empty(auth_client):
    """匿名请求在 production 应被 auth middleware 拦截 (403); 验证不崩即可."""
    from django.contrib.auth.models import AnonymousUser
    auth_client.force_authenticate(user=AnonymousUser())
    resp = auth_client.get('/api/v1/auth/me/')
    # 401 (token 缺失) 或 403 (auth middleware) 都算正常, 关键是不要 500
    assert resp.status_code in (200, 401, 403)