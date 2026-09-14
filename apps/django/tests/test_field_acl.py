"""Field ACL 服务测试 (PRD v4 §4.4 G43)"""
import pytest
from types import SimpleNamespace

from django.test import override_settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.field_acl.mixins import FieldAclSerializerMixin
from apps.field_acl.models import FieldACL, FieldAclAccessLog, FieldPermission
from apps.field_acl.services import FieldAclService
from apps.field_acl.views import FieldACLViewSet


@pytest.fixture(autouse=True)
def _clear_field_acl_cache():
    """FieldAclService.get_rules_map 用进程级 60s 缓存; 测试用例建/删 FieldACL 规则后
    缓存不会随事务回滚清空, 会污染同进程后续用例 (出现 "明明没建规则却命中 READ" 的明文泄漏假象)。
    每个用例结束后清掉规则缓存, 保证用例间隔离。"""
    yield
    FieldAclService.invalidate_rules_cache()


@pytest.mark.django_db
class TestFieldAclService:
    def test_superuser_sees_all(self, super_user):
        data = {'name': '张三', 'phone': '13800000000', 'email': 'a@b.com'}
        result = FieldAclService.apply_acl('candidate', data, super_user)
        assert result['phone'] == '13800000000'
        assert result['email'] == 'a@b.com'

    def test_default_mask_for_sensitive_fields(self, hr_user):
        data = {'name': '张三', 'phone': '13800000000', 'email': 'a@b.com'}
        result = FieldAclService.apply_acl('candidate', data, hr_user)
        assert '****' in result['phone']
        assert '***' in result['email']
        assert result['name'] == '张三'

    def test_explicit_none_permission_removes_field(self, hrbp_user):
        FieldACL.objects.create(
            entity='candidate', field='email',
            role_code='HRBP', permission=FieldPermission.NONE,
        )
        data = {'name': '张三', 'phone': '13800000000', 'email': 'secret@x.com'}
        result = FieldAclService.apply_acl('candidate', data, hrbp_user)
        assert 'email' not in result
        assert 'name' in result

    def test_mask_id_card(self, hr_user):
        data = {'id_card': '110101199001011234'}
        result = FieldAclService.apply_acl('candidate', data, hr_user)
        assert result['id_card'].startswith('110')
        assert result['id_card'].endswith('1234')
        assert '*' in result['id_card']

    def test_mask_salary(self, hr_user):
        data = {'salary': 25000}
        result = FieldAclService.apply_acl('offer', data, hr_user)
        assert result['salary'] == '***'

    def test_non_sensitive_field_passes_through(self, hr_user):
        data = {'name': '张三', 'level': 'P5', 'id': '12345'}
        result = FieldAclService.apply_acl('candidate', data, hr_user)
        assert result['name'] == '张三'
        assert result['level'] == 'P5'
        assert result['id'] == '12345'


@pytest.mark.django_db
class TestFieldAclEnforceAudit:
    """#8: 逐端点 strict (acl_strict 默认 fail-closed) / 列级可全局强制 / 补访问审计"""

    def test_acl_strict_default_is_fail_closed(self):
        assert FieldAclSerializerMixin.acl_strict is True

    def test_global_enforce_masks_sensitive_even_with_read_rule(self, hr_user):
        # HR 角色被显式放行 candidate.phone (READ) -> 默认下明文
        FieldACL.objects.create(
            entity='candidate', field='phone',
            role_code='HR', permission=FieldPermission.READ,
        )
        FieldAclService.invalidate_rules_cache('candidate')
        data = {'name': '张三', 'phone': '13800000000'}
        plain = FieldAclService.apply_acl('candidate', data, hr_user)
        assert plain['phone'] == '13800000000'  # 默认不强制, 按规则放行

        with override_settings(FIELD_ACL_GLOBAL_ENFORCE=True):
            masked = FieldAclService.apply_acl('candidate', data, hr_user)
        assert '****' in masked['phone']  # 全局强制 -> 脱敏

    def test_audit_logged_once_per_request(self, hr_user):
        req = SimpleNamespace(path='/api/v1/candidates/', META={'REMOTE_ADDR': '1.2.3.4'})
        data = {'name': '张三', 'phone': '13800000000', 'email': 'a@b.com'}
        FieldAclService.apply_acl('candidate', data, hr_user, request=req)
        FieldAclService.apply_acl('candidate', data, hr_user, request=req)  # 同 request -> 去重
        assert FieldAclAccessLog.objects.count() == 1
        log = FieldAclAccessLog.objects.first()
        assert set(log.masked_fields) == {'phone', 'email'}
        assert log.entity == 'candidate'
        assert log.user_id == str(hr_user.id)

    def test_superuser_access_is_audited(self, super_user):
        req = SimpleNamespace(path='/api/v1/candidates/', META={'REMOTE_ADDR': '1.2.3.4'})
        data = {'name': '张三', 'phone': '13800000000'}
        FieldAclService.apply_acl('candidate', data, super_user, request=req)
        assert FieldAclAccessLog.objects.count() == 1
        log = FieldAclAccessLog.objects.first()
        assert log.masked_fields == []  # 超管看明文, 脱敏字段为空
        assert log.user_id == str(super_user.id)

    def test_audit_endpoint_returns_logs(self, hr_user):
        FieldAclAccessLog.objects.create(
            entity='candidate', user_id=str(hr_user.id), username=hr_user.username,
            role_codes=['HR'], masked_fields=['phone'], hidden_fields=[],
            request_path='/api/v1/candidates/', client_ip='1.2.3.4',
        )
        req = Request(APIRequestFactory().get('/api/v1/field-acl/audit/?entity=candidate'))
        resp = FieldACLViewSet().audit(req)
        assert resp.data['success'] is True
        assert len(resp.data['data']) == 1
        assert resp.data['data'][0]['entity'] == 'candidate'
        assert resp.data['data'][0]['masked_fields'] == ['phone']
