"""Tests for PermissionBootstrap."""
import pytest
from django.core.exceptions import ImproperlyConfigured
from apps.core import bootstrap


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_bootstrap_missing_template_raises():
    """未 seed 时, 4 个模板都缺 → ImproperlyConfigured."""
    with pytest.raises(ImproperlyConfigured, match='V2 templates missing'):
        bootstrap.bootstrap_permission_v2()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_bootstrap_missing_resources_raises():
    """模板齐 + 资源 < 50 → ImproperlyConfigured."""
    from apps.core.models_permission_v2 import PermissionTemplate, TenantConfig, PermissionResource
    # 加齐 4 个模板
    for code in ('TMPL_ADMIN', 'TMPL_DIRECTOR', 'TMPL_SPECIALIST', 'TMPL_INTERVIEWER'):
        PermissionTemplate.objects.create(
            system_code='recruit',
            template_code=code,
            template_name=code,
            is_system=1,
            permission_codes=['recruit:candidate:list'],
        )
    # 加 GLOBAL_DEFAULT_DATA_SCOPE 配置 (避免第 3 检查触发)
    TenantConfig.objects.create(
        system_code='recruit',
        config_key='GLOBAL_DEFAULT_DATA_SCOPE',
        config_value='SELF',
    )
    # 只加 1 条 resource (触发第 2 检查: cnt < 50)
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test:menu:view',
        resource_name='T',
        resource_type='MENU',
        module='test',
    )
    with pytest.raises(ImproperlyConfigured, match='V2 resources only 1, need >= 50'):
        bootstrap.bootstrap_permission_v2()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_bootstrap_all_checks_pass():
    """4 模板 + 50 资源 + tenant config 齐 → 不抛错."""
    from apps.core.models_permission_v2 import PermissionTemplate, TenantConfig, PermissionResource
    for code in ('TMPL_ADMIN', 'TMPL_DIRECTOR', 'TMPL_SPECIALIST', 'TMPL_INTERVIEWER'):
        PermissionTemplate.objects.create(
            system_code='recruit',
            template_code=code,
            template_name=code,
            is_system=1,
            permission_codes=['recruit:candidate:list'],
        )
    TenantConfig.objects.create(
        system_code='recruit',
        config_key='GLOBAL_DEFAULT_DATA_SCOPE',
        config_value='SELF',
    )
    for i in range(50):
        PermissionResource.objects.create(
            system_code='recruit',
            resource_code=f'recruit:test{i}:menu:view',
            resource_name=f'R{i}',
            resource_type='MENU',
            module='test',
        )
    # 不应抛错
    bootstrap.bootstrap_permission_v2()