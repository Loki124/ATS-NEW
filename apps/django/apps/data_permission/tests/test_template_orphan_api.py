"""模板删除/恢复端点的 HTTP 层契约（2026-10-12）。

验证薄封装层没把语义做歪：
  - DELETE 软删模板 -> 引用条件组被置失效，并回传影响面数量
  - POST /restore/   -> 解除失效标记，规则复活
  - 恢复非软删模板 -> restored=False（幂等，不报错）
  - 未登录/非超管   -> 403（IsSuperAdmin 闸门不被绕过）
"""
import pytest
from rest_framework import status

from apps.core.models import Department, User
from apps.data_permission.models import DataPermissionRule, DataPermTemplate, RowScopeType
from apps.data_permission.scope_templates import build_template_ref, instantiate

TPL_LIST = '/api/v1/data-permissions/templates/'


@pytest.fixture
def tpl(db):
    return DataPermTemplate.objects.create(
        code='TPL_API', name='测试用模板', module_key='demand',
        params=[{'key': 'relation', 'label': '包含关系', 'required': True, 'default': 'contains'}],
        groups=[{'expr': '', 'conditions': [
            {'kind': 'relationship', 'dimension': 'dept', 'valueSource': 'dynamic',
             'dynamicKey': 'currentUser.departments', 'relation': '${relation}'},
        ]}],
    )


@pytest.fixture
def rule_referencing(tpl):
    user = User.objects.create(username='orphan_api')
    groups = instantiate(tpl, {'relation': 'contains'})
    return DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value='HRBP', level='ROW', entity='demand',
        scope_type=RowScopeType.CUSTOM,
        scope_payload={'expr': '', 'groups': [{
            'expr': '',
            'templateRef': build_template_ref(tpl, {'relation': 'contains'}),
            'conditions': groups[0]['conditions'],
        }]},
        created_by=user.pk,
    )


def _orphaned(rule):
    rule.refresh_from_db()
    return bool(rule.scope_payload['groups'][0]['templateRef'].get('orphaned'))


def test_delete_soft_deletes_and_orphans_references(auth_client, tpl, rule_referencing):
    resp = auth_client.delete(f'{TPL_LIST}{tpl.id}/')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['success'] is True
    assert resp.data['data']['orphanedConditions'] == 1
    assert DataPermTemplate.all_objects.get(pk=tpl.pk).deleted_at is not None
    assert _orphaned(rule_referencing) is True


def test_soft_deleted_template_hidden_from_list(auth_client, tpl, rule_referencing):
    auth_client.delete(f'{TPL_LIST}{tpl.id}/')
    resp = auth_client.get(TPL_LIST)
    payload = resp.data['data']
    # 分页与否两种形态都兼容（数据量小时 DRF 可能直接给 list）
    rows = payload['results'] if isinstance(payload, dict) else payload
    codes = [row['code'] for row in rows]
    assert 'TPL_API' not in codes


def test_restore_clears_orphan_and_revives(auth_client, tpl, rule_referencing):
    auth_client.delete(f'{TPL_LIST}{tpl.id}/')
    assert _orphaned(rule_referencing) is True

    resp = auth_client.post(f'{TPL_LIST}{tpl.id}/restore/', {}, format='json')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['data']['restored'] is True
    assert resp.data['data']['revivedConditions'] == 1
    assert _orphaned(rule_referencing) is False


def test_restore_is_idempotent(auth_client, tpl, rule_referencing):
    resp = auth_client.post(f'{TPL_LIST}{tpl.id}/restore/', {}, format='json')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['data']['restored'] is False


def test_restore_unknown_id_404(auth_client, db):
    resp = auth_client.post(f'{TPL_LIST}nonexistent-id/restore/', {}, format='json')
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_anonymous_cannot_delete(super_user, client, tpl, rule_referencing):
    resp = client.delete(f'{TPL_LIST}{tpl.id}/')
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert _orphaned(rule_referencing) is False, '未授权不得改动引用方'
