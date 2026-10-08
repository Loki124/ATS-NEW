"""Tests for seed_v2_init command."""
import pytest
from django.core.management import call_command


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_seed_creates_resources_templates_tenant():
    call_command('seed_v2_init')
    from apps.core.models_permission_v2 import (
        PermissionResource,
        PermissionTemplate,
        TenantConfig,
    )
    assert PermissionResource.objects.count() >= 60
    assert PermissionTemplate.objects.filter(
        template_code__in=['TMPL_ADMIN', 'TMPL_DIRECTOR', 'TMPL_SPECIALIST', 'TMPL_INTERVIEWER'],
    ).count() == 4
    assert TenantConfig.objects.filter(
        config_key='GLOBAL_DEFAULT_DATA_SCOPE',
    ).exists()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_seed_is_idempotent():
    from apps.core.models_permission_v2 import PermissionResource
    call_command('seed_v2_init')
    n1 = PermissionResource.objects.count()
    call_command('seed_v2_init')
    n2 = PermissionResource.objects.count()
    assert n1 == n2


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_seed_tmpl_admin_has_all_resources():
    call_command('seed_v2_init')
    from apps.core.models_permission_v2 import (
        PermissionResource,
        PermissionTemplate,
    )
    admin = PermissionTemplate.objects.get(template_code='TMPL_ADMIN')
    all_codes = set(PermissionResource.objects.values_list('resource_code', flat=True))
    assert set(admin.permission_codes) == all_codes