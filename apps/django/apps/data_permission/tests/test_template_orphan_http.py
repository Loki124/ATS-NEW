"""「模板删除即失效」HTTP 层契约 (2026-10-12).

覆盖：
  - DELETE /templates/{pk}/        -> 软删 + orphanedConditions 计数 + 引用组被打 orphaned
  - POST  /templates/{pk}/restore/ -> 复活 + revivedConditions 计数 + 标记摘除
  - 边界：未删除模板 restore 返回 restored=False；不存在返回 404
"""
import pytest
from rest_framework import status

from apps.core.models import Department, User
from apps.data_permission.models import (
    DataPermissionRule,
    DataPermTemplate,
    RowScopeType,
)
from apps.data_permission.scope_templates import build_template_ref, instantiate

TPL_LIST = '/api/v1/data-permissions/templates/'


@pytest.fixture
def tpl(db):
    dept = Department.objects.create(name='智能BG')
    user = User.objects.create(username='orphan_http_actor', department=dept)
    template = DataPermTemplate.objects.create(
        code='TPL_HTTP', name='HTTP测试模板', module_key='demand',
        groups=[{'expr': '', 'conditions': [
            {'kind': 'relationship', 'dimension': 'dept', 'valueSource': 'dynamic',
             'dynamicKey': 'currentUser.departments', 'relation': 'contains'},
        ]}],
    )
    return template, user


def _rule_referencing(template, user):
    g = instantiate(template, {})
    return DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value='HRBP', level='ROW', entity='demand',
        scope_type=RowScopeType.CUSTOM,
        scope_payload={'expr': '', 'groups': [
            {'expr': '', 'templateRef': build_template_ref(template, {}),
             'conditions': g[0]['conditions']},
        ]},
        created_by=user.pk,
    )


def test_delete_template_orphans_referencing_group(auth_client, tpl):
    template, user = tpl
    rule = _rule_referencing(template, user)

    resp = auth_client.delete(f'{TPL_LIST}{template.pk}/')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['success'] is True
    assert resp.data['data']['orphanedConditions'] == 1
    assert resp.data['data']['code'] == template.code

    rule.refresh_from_db()
    assert rule.scope_payload['groups'][0]['templateRef']['orphaned'] is True


def test_restore_revives_referencing_group(auth_client, tpl):
    template, user = tpl
    rule = _rule_referencing(template, user)
    auth_client.delete(f'{TPL_LIST}{template.pk}/')

    resp = auth_client.post(f'{TPL_LIST}{template.pk}/restore/')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['success'] is True
    assert resp.data['data']['restored'] is True
    assert resp.data['data']['revivedConditions'] == 1

    rule.refresh_from_db()
    assert 'orphaned' not in rule.scope_payload['groups'][0]['templateRef']


def test_restore_idempotent_when_not_deleted(auth_client, tpl):
    template, _ = tpl
    resp = auth_client.post(f'{TPL_LIST}{template.pk}/restore/')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['data']['restored'] is False


def test_restore_missing_returns_404(auth_client):
    resp = auth_client.post(f'{TPL_LIST}999999/restore/')
    assert resp.status_code == status.HTTP_404_NOT_FOUND
