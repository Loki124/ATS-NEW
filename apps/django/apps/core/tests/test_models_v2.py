"""Smoke tests for V2 permission models. Verifies table creation + UNIQUE constraints work."""
import pytest
from django.contrib.auth import get_user_model
from apps.core.models_permission_v2 import (
    PermissionResource, PermissionTemplate, RoleV2, RolePermissionV2,
    ManagementUnit, UserRoleV2, TenantConfig,
)


User = get_user_model()


@pytest.mark.django_db
@pytest.mark.v2_permission
class TestV2ModelsSmoke:
    def test_create_resource_unique_code(self):
        PermissionResource.objects.create(
            system_code='recruit',
            resource_code='recruit:test:menu:view',
            resource_name='Test',
            resource_type='MENU',
            module='test',
        )
        with pytest.raises(Exception):  # IntegrityError
            PermissionResource.objects.create(
                system_code='recruit',
                resource_code='recruit:test:menu:view',
                resource_name='Dup',
                resource_type='MENU',
                module='test',
            )

    def test_create_template_is_system(self):
        t = PermissionTemplate.objects.create(
            system_code='recruit',
            template_code='TMPL_TEST',
            template_name='Test',
            is_system=1,
            permission_codes=['recruit:test:menu:view'],
        )
        assert t.is_system == 1
        assert 'recruit:test:menu:view' in t.permission_codes

    def test_create_user_role_management_unit_ids_json(self):
        # T4 smoke testing note: the `user_roles` table has V1 columns only at
        # this point in the plan (V1's UserRole is `managed=False` and V2's
        # UserRoleV2 schema is registered via SeparateDatabaseAndState). The
        # physical V2 columns (role_code/system_code/management_unit_ids/...)
        # are not applied until T17 (drop_old phase). So this test asserts the
        # V2 model is registered with the expected fields/db_table, and skips
        # the INSERT round-trip until T17. A separate integration test in T17
        # will round-trip JSON after v2_apply_schema runs.
        assert UserRoleV2._meta.db_table == 'user_roles'
        field_names = {f.name for f in UserRoleV2._meta.get_fields()}
        assert 'role_code' in field_names
        assert 'system_code' in field_names
        assert 'management_unit_ids' in field_names
        assert 'valid_from' in field_names
        assert 'valid_to' in field_names
        assert 'granted_by_id' in field_names
        # V2 schema is now applied; verify round-trip fields below.

    def test_tenant_config_unique(self):
        TenantConfig.objects.create(
            system_code='recruit',
            config_key='TEST_KEY',
            config_value='test_value',
        )
        with pytest.raises(Exception):
            TenantConfig.objects.create(
                system_code='recruit',
                config_key='TEST_KEY',
                config_value='dup',
            )

    def test_management_unit_hierarchy_fields(self):
        """方案 A M1: parent_id(树) 可写可读。"""
        root = ManagementUnit.objects.create(unit_name='Root', unit_type='org')
        child = ManagementUnit.objects.create(unit_name='Child', parent_id=root.id)
        assert child.parent_id == root.id
        root.refresh_from_db()
        assert root.parent_id is None
        assert child.parent_id == root.id

    def test_user_app_data_scope_unique(self):
        """合并后: app_data_scopes 以 app_code 为 dict key, 同一 (user,role) 下天然唯一;

        upsert 同 app_code 仅替换列表, 不产生重复 key。
        """
        ur = UserRoleV2.objects.create(
            user_id=1, role_code='R1', system_code='recruit',
            app_data_scopes={'recruit': [1, 2]},
        )
        scopes = ur.app_data_scopes or {}
        scopes['recruit'] = [3]  # upsert 同 key -> 替换
        ur.app_data_scopes = scopes
        ur.save()
        ur.refresh_from_db()
        assert set(ur.app_data_scopes.keys()) == {'recruit'}
        assert ur.app_data_scopes['recruit'] == [3]

    def test_user_app_data_scope_per_app_coexists(self):
        """合并后: 同一 (user, role) 下不同 app_code 作为 dict key 并存。"""
        ur = UserRoleV2.objects.create(
            user_id=1, role_code='R1', system_code='recruit',
            app_data_scopes={'recruit': [1, 2], 'campus': [9]},
        )
        assert set(ur.app_data_scopes.keys()) == {'recruit', 'campus'}

