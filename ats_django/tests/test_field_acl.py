"""Field ACL 服务测试 (PRD v4 §4.4 G43)"""
import pytest

from apps.field_acl.models import FieldACL, FieldPermission
from apps.field_acl.services import FieldAclService


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
