"""Batch F 信封收口测试: dynamic_field 4 个 ViewSet 的 C/U/R 须返回统一信封。

统一契约: {"success": true, "data": <payload>, "message": "", "code": 0}
覆盖:
  - DynamicFieldViewSet     (list / create / retrieve / update(PATCH))
  - FieldModuleViewSet      (_DataEnvelopeMixin: list / create / retrieve / update)
  - FieldGroupViewSet       (_DataEnvelopeMixin: create / retrieve)
  - FieldLinkageRuleViewSet (_DataEnvelopeMixin: create / retrieve)

判定黄金标准: 响应体必须含 ``code`` 字段且 == 0 (缺 code 即半信封未收口)。
"""
from apps.common.tests.envelope_contract import assert_envelope
import pytest

from apps.dynamic_field.models import DynamicField, FieldModule

RESOURCE = 'Candidate'
FIELDS_LIST = f'/api/v1/dynamic-fields/{RESOURCE}/fields/'
MODULES_LIST = f'/api/v1/dynamic-fields/{RESOURCE}/modules/'
GROUPS_LIST = f'/api/v1/dynamic-fields/{RESOURCE}/groups/'
LINKAGE_LIST = f'/api/v1/dynamic-fields/{RESOURCE}/linkage-rules/'



def _field_payload(**overrides) -> dict:
    """与前端表单一致的 camelCase payload (对齐 test_dynamic_field_api.build_payload)。"""
    payload = {
        'fieldKey': 'df_env_key',
        'label': '信封测试字段',
        'fieldType': 'TEXT',
        'isRequired': False,
        'isVisible': True,
        'placeholder': '请输入',
        'helpText': 'envelope test',
        'defaultValue': '',
        'orderIndex': 0,
        'groupName': '基本信息',
        'options': [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestDynamicFieldEnvelope:
    """DynamicFieldViewSet — 自定义 C/U/R (含系统字段守卫), 收敛到 success_response。"""

    def test_list_envelope(self, auth_client):
        DynamicField.objects.create(
            resource=RESOURCE, field_key='df_env_l', label='EnvList',
            field_type=DynamicField.FieldType.TEXT, order_index=0,
        )
        resp = auth_client.get(FIELDS_LIST)
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert_envelope(body)
        assert isinstance(body['data'], list)

    def test_create_envelope(self, auth_client):
        resp = auth_client.post(FIELDS_LIST, _field_payload(fieldKey='df_env_c'), format='json')
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert_envelope(body, code=0)
        assert body['data']['fieldKey'] == 'df_env_c'

    def test_retrieve_envelope(self, auth_client):
        f = DynamicField.objects.create(
            resource=RESOURCE, field_key='df_env_r', label='EnvRetrieve',
            field_type=DynamicField.FieldType.TEXT, order_index=0,
        )
        resp = auth_client.get(f'{FIELDS_LIST}{f.id}/')
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert_envelope(body)
        assert body['data']['id'] == f.id

    def test_update_patch_envelope(self, auth_client):
        f = DynamicField.objects.create(
            resource=RESOURCE, field_key='df_env_u', label='EnvUpdate',
            field_type=DynamicField.FieldType.TEXT, order_index=0,
        )
        resp = auth_client.patch(f'{FIELDS_LIST}{f.id}/', {'label': 'EnvUpdate-改'}, format='json')
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert_envelope(body)
        assert body['data']['label'] == 'EnvUpdate-改'


@pytest.mark.django_db
class TestFieldModuleEnvelope:
    """FieldModuleViewSet — _DataEnvelopeMixin 收口。"""

    def _create_module(self, client):
        payload = {'name': 'ModEnv', 'code': 'mod_env', 'orderIndex': 0, 'isActive': True}
        resp = client.post(MODULES_LIST, payload, format='json')
        assert resp.status_code == 201, resp.content
        return resp.json()['data']['id']

    def test_list_envelope(self, auth_client):
        self._create_module(auth_client)
        resp = auth_client.get(MODULES_LIST)
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert_envelope(body)
        assert isinstance(body['data'], list)

    def test_create_envelope(self, auth_client):
        payload = {'name': 'ModEnv2', 'code': 'mod_env2', 'orderIndex': 0, 'isActive': True}
        resp = auth_client.post(MODULES_LIST, payload, format='json')
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert_envelope(body, code=0)
        assert body['data']['name'] == 'ModEnv2'

    def test_retrieve_envelope(self, auth_client):
        mid = self._create_module(auth_client)
        resp = auth_client.get(f'{MODULES_LIST}{mid}/')
        assert resp.status_code == 200, resp.content
        assert_envelope(resp.json())

    def test_update_patch_envelope(self, auth_client):
        mid = self._create_module(auth_client)
        resp = auth_client.patch(f'{MODULES_LIST}{mid}/', {'name': 'ModEnv-改'}, format='json')
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert_envelope(body)
        assert body['data']['name'] == 'ModEnv-改'


@pytest.mark.django_db
class TestFieldGroupEnvelope:
    """FieldGroupViewSet — _DataEnvelopeMixin 收口 (FK 须 module_id)。"""

    def _make_module(self, auth_client):
        return FieldModule.objects.create(
            resource=RESOURCE, code='grp_mod_env', name='GrpModEnv', order_index=0,
        )

    def test_create_envelope(self, auth_client):
        mod = self._make_module(auth_client)
        payload = {'name': 'GrpEnv', 'moduleId': mod.id}
        resp = auth_client.post(GROUPS_LIST, payload, format='json')
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert_envelope(body, code=0)
        assert body['data']['name'] == 'GrpEnv'

    def test_retrieve_envelope(self, auth_client):
        mod = self._make_module(auth_client)
        payload = {'name': 'GrpEnvR', 'moduleId': mod.id}
        created = auth_client.post(GROUPS_LIST, payload, format='json')
        assert created.status_code == 201, created.content
        gid = created.json()['data']['id']
        resp = auth_client.get(f'{GROUPS_LIST}{gid}/')
        assert resp.status_code == 200, resp.content
        assert_envelope(resp.json())


@pytest.mark.django_db
class TestFieldLinkageRuleEnvelope:
    """FieldLinkageRuleViewSet — _DataEnvelopeMixin 收口。"""

    def _make_module(self, auth_client):
        return FieldModule.objects.create(
            resource=RESOURCE, code='lk_mod_env', name='LkModEnv', order_index=0,
        )

    def _create_linkage(self, auth_client, mod):
        payload = {
            'name': 'LkEnv',
            'moduleId': mod.id,
            'conditionMode': 'ALL',
            'conditions': [],
            'actions': [],
            'orderIndex': 0,
            'isActive': True,
        }
        resp = auth_client.post(LINKAGE_LIST, payload, format='json')
        assert resp.status_code == 201, resp.content
        return resp.json()['data']['id']

    def test_create_envelope(self, auth_client):
        mod = self._make_module(auth_client)
        payload = {
            'name': 'LkEnvC',
            'moduleId': mod.id,
            'conditionMode': 'ALL',
            'conditions': [],
            'actions': [],
            'orderIndex': 0,
            'isActive': True,
        }
        resp = auth_client.post(LINKAGE_LIST, payload, format='json')
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert_envelope(body, code=0)
        assert body['data']['name'] == 'LkEnvC'

    def test_retrieve_envelope(self, auth_client):
        mod = self._make_module(auth_client)
        lid = self._create_linkage(auth_client, mod)
        resp = auth_client.get(f'{LINKAGE_LIST}{lid}/')
        assert resp.status_code == 200, resp.content
        assert_envelope(resp.json())
