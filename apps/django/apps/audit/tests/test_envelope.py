"""Audit 信封契约测试 (P1-3 A2)

验证 AuditLogViewSet 经 EnvelopeReadOnlyMixin 后:
- retrieve 返回统一信封 {success, data, ...}（不再裸 serializer.data）
- list 已由 StandardResultsSetPagination 包信封 (回归守住)

鉴权用全局 auth_client (super_user, 过 IsSuperAdmin)。
"""
import pytest

from apps.audit.models import AuditLog

AUDIT_LIST = '/api/v1/audit-logs/'

pytestmark = pytest.mark.django_db


@pytest.fixture
def audit_log(db):
    return AuditLog.objects.create(
        action='CREATE', entity='Candidate', entity_id='cand-1', field='name',
    )


def test_retrieve_audit_envelope(auth_client, audit_log):
    resp = auth_client.get(f'{AUDIT_LIST}{audit_log.id}/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['id'] == str(audit_log.id)
    assert body['data']['action'] == 'CREATE'
    assert body['data']['entity'] == 'Candidate'


def test_list_audit_envelope(auth_client, audit_log):
    resp = auth_client.get(AUDIT_LIST, {'page_size': 200})
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert isinstance(body['data'], list)
    assert body['pagination']['total'] >= 1
