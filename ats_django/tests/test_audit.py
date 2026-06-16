"""Audit app 测试 (PRD v4 §13)"""
import pytest

from apps.audit.models import AuditLog
from apps.audit.services import AuditService


@pytest.mark.django_db
class TestAuditService:
    def test_record_log(self, hr_user):
        log = AuditService.record(
            user=hr_user,
            action='CREATE',
            entity='candidate',
            entity_id='cand-001',
            ip='127.0.0.1',
            user_agent='Mozilla/5.0',
        )
        assert log.id is not None
        assert log.action == 'CREATE'
        assert log.user == hr_user
        assert log.entity == 'candidate'

    def test_query_logs(self, hr_user):
        for i in range(3):
            AuditService.record(
                user=hr_user,
                action='CREATE',
                entity='candidate',
                entity_id=f'cand-{i:03d}',
            )
        results = AuditService.query(user_id=hr_user.id, limit=10)
        assert len(results) == 3

    def test_filter_by_action(self, hr_user):
        AuditService.record(user=hr_user, action='CREATE', entity='candidate', entity_id='a')
        AuditService.record(user=hr_user, action='UPDATE', entity='candidate', entity_id='a')
        AuditService.record(user=hr_user, action='DELETE', entity='candidate', entity_id='a')
        results = AuditService.query(action='UPDATE')
        assert len(results) == 1
        assert results[0].action == 'UPDATE'

    def test_get_entity_history(self, hr_user):
        for i in range(5):
            AuditService.record(
                user=hr_user,
                action='UPDATE',
                entity='candidate',
                entity_id='cand-X',
                field=f'field_{i}',
                old_value=f'old_{i}',
                new_value=f'new_{i}',
            )
        history = AuditService.get_entity_history('candidate', 'cand-X')
        assert len(history) == 5
        assert all(h.entity_id == 'cand-X' for h in history)


@pytest.mark.django_db
class TestAuditAPI:
    def test_audit_log_list_requires_superuser(self, auth_hr_client):
        """HR 角色访问审计日志应被拒绝"""
        response = auth_hr_client.get('/api/v1/audit-logs/')
        assert response.status_code == 403

    def test_audit_log_list_superuser(self, auth_client, hr_user):
        # 先创建一些审计日志
        for i in range(2):
            AuditService.record(user=hr_user, action='CREATE', entity='candidate', entity_id=str(i))
        response = auth_client.get('/api/v1/audit-logs/')
        assert response.status_code == 200
        assert response.data['success'] is True
