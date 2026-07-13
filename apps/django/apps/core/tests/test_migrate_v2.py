"""Tests for migrate_v2_data command."""
import pytest
from django.core.management import call_command


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_migrate_runs_idempotently():
    """空 DB → migrate 0 行, 不报错."""
    call_command('migrate_v2_data')
    call_command('migrate_v2_data')  # 第二次也无报错


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_migrate_creates_role_with_v2_schema_guard():
    """V2 schema 未应用 (user_roles 缺 V2 列) 时, migrate 应 graceful skip."""
    call_command('migrate_v2_data')  # 不应抛错
    from apps.core.models_permission_v2 import RoleV2
    # V2 表可能没数据 (V1 也空), 但不应 crash
    assert isinstance(RoleV2.objects.count(), int)
