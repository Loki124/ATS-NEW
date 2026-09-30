"""mou 信封契约: 经 EnvelopeWriteMixin, create(201)/update(200)/retrieve(200) 包 {success,data,code}.

list 由 StandardResultsSetPagination 信封 (data 为 list + pagination).
使用 auth_hrbp_client: MOUVIEWSetPermission 要求 HRBP+(HRBP_TIER 含 HRBP/SUPER_ADMIN),
HRBP 同时落入 HR_TIER 故安全方法也可达.
"""
import pytest

from apps.mou.models import MouAgreement, MouContainer, MutualExclusionGroup, MouRule


def _assert_envelope(body, code=0):
    assert body.get('success') is True
    assert 'data' in body
    assert body.get('code') == code


@pytest.mark.django_db
def test_mou_agreement_list(auth_hrbp_client):
    MouAgreement.objects.create(code='MOU-LIST-001', company_name='C1')
    resp = auth_hrbp_client.get('/api/v1/permissions-v2/mou/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
    assert isinstance(resp.json()['data'], list)


@pytest.mark.django_db
def test_mou_agreement_create_retrieve_update(auth_hrbp_client):
    # create -> 201, 信封含 data.id
    resp = auth_hrbp_client.post(
        '/api/v1/permissions-v2/mou/', {'code': 'MOU-CU-001'}, format='json')
    assert resp.status_code == 201
    body = resp.json()
    _assert_envelope(body)
    pk = body['data']['id']
    assert body['data']['code'] == 'MOU-CU-001'

    # retrieve -> 200, 信封
    resp = auth_hrbp_client.get(f'/api/v1/permissions-v2/mou/{pk}/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
    assert resp.json()['data']['id'] == pk

    # update (PATCH) -> 200, 信封; camelCase 字段回落 snake
    resp = auth_hrbp_client.patch(
        f'/api/v1/permissions-v2/mou/{pk}/', {'companyName': 'C2'}, format='json')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
    assert resp.json()['data']['companyName'] == 'C2'


@pytest.mark.django_db
def test_mou_container_create_retrieve(auth_hrbp_client):
    mou = MouAgreement.objects.create(id='mou_con_001', code='MOU-CON-001', company_name='C')
    resp = auth_hrbp_client.post(
        '/api/v1/permissions-v2/containers/',
        {'mou': mou.id, 'code': 'CON-001', 'positionTitle': '后端工程师'},
        format='json')
    assert resp.status_code == 201
    _assert_envelope(resp.json())
    pk = resp.json()['data']['id']
    resp = auth_hrbp_client.get(f'/api/v1/permissions-v2/containers/{pk}/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
    assert resp.json()['data']['positionTitle'] == '后端工程师'


@pytest.mark.django_db
def test_mutual_exclusion_group_create_retrieve(auth_hrbp_client):
    resp = auth_hrbp_client.post(
        '/api/v1/permissions-v2/mutual-exclusion-groups/',
        {'name': 'MTX-001', 'members': ['a', 'b']}, format='json')
    assert resp.status_code == 201
    _assert_envelope(resp.json())
    pk = resp.json()['data']['id']
    resp = auth_hrbp_client.get(f'/api/v1/permissions-v2/mutual-exclusion-groups/{pk}/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())


@pytest.mark.django_db
def test_mou_rule_create_retrieve(auth_hrbp_client):
    resp = auth_hrbp_client.post(
        '/api/v1/permissions-v2/automation-rules/',
        {'name': 'RULE-001', 'triggerEvent': 'stage-entered'}, format='json')
    assert resp.status_code == 201
    _assert_envelope(resp.json())
    pk = resp.json()['data']['id']
    resp = auth_hrbp_client.get(f'/api/v1/permissions-v2/automation-rules/{pk}/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
