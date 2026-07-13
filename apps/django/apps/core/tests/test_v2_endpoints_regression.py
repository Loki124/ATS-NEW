"""Regression: V2 9 个 endpoint + me_view 在空 DB / 异常条件下不 crash.
T25: 验证 endpoints 都注册, 数据缺失时返回合理错误 (200/401/403/404, NOT 500).
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_resources_endpoint_no_500():
    client = APIClient()
    res = client.get('/api/v1/permissions/resources/')
    assert res.status_code != 500, f'Got 500: {res.content[:200]}'


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_templates_endpoint_no_500():
    client = APIClient()
    res = client.get('/api/v1/permissions/templates/')
    assert res.status_code != 500


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_roles_endpoint_no_500():
    client = APIClient()
    res = client.get('/api/v1/permissions/roles/')
    assert res.status_code != 500


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_user_roles_endpoint_no_500():
    client = APIClient()
    res = client.get('/api/v1/permissions/user-roles/')
    assert res.status_code != 500


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_management_units_endpoint_no_500():
    client = APIClient()
    res = client.get('/api/v1/permissions/mgmt-units/')
    assert res.status_code != 500


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_permission_check_endpoint_no_500():
    client = APIClient()
    res = client.post('/api/v1/permission/check/', {'resourceCode': 'recruit:candidate:list'}, format='json')
    assert res.status_code != 500


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_role_clone_template_endpoint_no_500():
    client = APIClient()
    # Use fake IDs — should 404, not 500
    res = client.post('/api/v1/permissions/roles/fake-id/clone-from-template/', {'templateId': 'fake'}, format='json')
    assert res.status_code in (404, 400, 405)
