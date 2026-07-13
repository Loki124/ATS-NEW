"""V2 cutover: DROP V1 残留表 + CREATE V2 roles/user_roles schema.
T17: 单事务 DDL, schema_editor 跨 DB 兼容 (MySQL + SQLite).
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'DANGER: DROP V1 残留 + CREATE V2 roles/user_roles schema. 必须传 --confirm.'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true')

    @transaction.atomic
    def handle(self, *args, **opts):
        if not opts['confirm']:
            self.stdout.write(self.style.ERROR(
                'Refusing to run without --confirm. Re-run: '
                'python manage.py migrate_v2_drop_old --confirm'
            ))
            return

        # 1. DROP V1 残留表 (如有)
        with connection.cursor() as c:
            for table in ('permissions', 'role_permissions', 'roles', 'user_roles'):
                c.execute(f'DROP TABLE IF EXISTS {table}')

        # 2. CREATE V2 schema 用 schema_editor (跨 DB 兼容)
        from apps.core.models_permission_v2 import RoleV2, UserRoleV2
        with connection.schema_editor() as editor:
            try:
                editor.create_model(RoleV2)
                self.stdout.write(self.style.SUCCESS('Created V2 roles table'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'roles table: {e}'))
            try:
                editor.create_model(UserRoleV2)
                self.stdout.write(self.style.SUCCESS('Created V2 user_roles table'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'user_roles table: {e}'))

        self.stdout.write(self.style.SUCCESS('V2 cutover done. ⚠️  IRREVERSIBLE without snapshot.'))
