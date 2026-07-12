"""V1 → V2 数据迁移命令. Idempotent.
T16: 拷贝 V1 Role / RolePermission / UserRole 数据到 V2 表.
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = '从 V1 表迁移数据到 V2 表. Idempotent (update_or_create).'

    @transaction.atomic
    def handle(self, *args, **opts):
        from django.db.utils import OperationalError, ProgrammingError
        # V1 models (managed=False, 但能读)
        from apps.core.models import Role, RolePermission, UserRole
        # V2 models
        from apps.core.models_permission_v2 import (
            RoleV2, RolePermissionV2, UserRoleV2, ManagementUnit,
        )

        n_roles = n_role_perms = n_user_roles = n_units = 0

        # 1. V1 Role → V2 RoleV2 (注意 V2 columns: role_code/role_name, V1 是 code/name)
        try:
            for r in Role.objects.all():
                _, created = RoleV2.objects.update_or_create(
                    role_code=r.code, system_code='recruit',
                    defaults={
                        'role_name': r.name,
                        'description': r.description or '',
                        'is_system': 1 if getattr(r, 'is_builtin', False) else 0,
                        'status': 1 if getattr(r, 'is_active', True) else 0,
                    },
                )
                if created:
                    n_roles += 1
        except (OperationalError, ProgrammingError, AttributeError) as e:
            self.stdout.write(self.style.WARNING(f'Role skip: {e}'))

        # 2. V1 RolePermission → V2 RolePermissionV2
        try:
            rps = RolePermission.objects.select_related('role', 'permission').all()
            for rp in rps:
                role_code = getattr(rp.role, 'code', None) or getattr(rp, 'role_code', None)
                perm_code = getattr(rp.permission, 'code', None) or getattr(rp, 'permission_code', None)
                if not (role_code and perm_code):
                    continue
                _, created = RolePermissionV2.objects.update_or_create(
                    role_code=role_code, resource_code=perm_code, system_code='recruit',
                    defaults={},
                )
                if created:
                    n_role_perms += 1
        except (OperationalError, ProgrammingError, AttributeError) as e:
            self.stdout.write(self.style.WARNING(f'RolePermission skip: {e}'))

        # 3. V1 UserRole → V2 UserRoleV2 (dept → auto-created ManagementUnit)
        try:
            urs = UserRole.objects.select_related('user', 'role', 'department').all()
            for ur in urs:
                user_id = ur.user_id
                role_code = getattr(ur.role, 'code', None) or getattr(ur, 'role_code', None)
                if not (user_id and role_code):
                    continue
                unit_ids = []
                dept = getattr(ur, 'department', None)
                if dept:
                    unit_name = f'auto_migrated:{dept.name}'
                    unit, _ = ManagementUnit.objects.get_or_create(
                        unit_name=unit_name,
                        defaults={
                            'system_code': 'recruit',
                            'unit_type': 'org',
                            'org_scope': [dept.id],
                            'include_children': 1,
                            'status': 1,
                        },
                    )
                    unit_ids = [unit.id]
                    n_units += 1
                _, created = UserRoleV2.objects.update_or_create(
                    user_id=user_id, role_code=role_code, system_code='recruit',
                    defaults={
                        'management_unit_ids': unit_ids or None,
                        'granted_by_id': getattr(ur, 'granted_by_id', None),
                    },
                )
                if created:
                    n_user_roles += 1
        except (OperationalError, ProgrammingError, AttributeError) as e:
            self.stdout.write(self.style.WARNING(f'UserRole skip: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'Migration OK: {n_roles} roles, {n_role_perms} role_permissions, '
            f'{n_user_roles} user_roles, {n_units} auto-created units'
        ))
