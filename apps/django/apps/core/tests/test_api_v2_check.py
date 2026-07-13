"""Test for /permission/check endpoint."""
import pytest


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_check_superuser_returns_true(auth_client, super_user):
    """super_user is_superuser=True → has_perm bypass → True."""
    resp = auth_client.post(
        '/api/v1/permission/check/',
        data={'user_id': super_user.id, 'resource_code': 'recruit:foo:menu:view'},
        format='json',
    )
    assert resp.status_code == 200
    body = resp.json()
    data = body['data'] if isinstance(body, dict) and 'data' in body else body
    assert data['hasPermission'] is True


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_check_unknown_user_returns_404(auth_client):
    resp = auth_client.post(
        '/api/v1/permission/check/',
        data={'user_id': 999999, 'resource_code': 'recruit:foo:menu:view'},
        format='json',
    )
    assert resp.status_code == 404


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_check_missing_params_returns_400(auth_client):
    resp = auth_client.post(
        '/api/v1/permission/check/',
        data={},
        format='json',
    )
    assert resp.status_code == 400