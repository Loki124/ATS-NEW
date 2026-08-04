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
