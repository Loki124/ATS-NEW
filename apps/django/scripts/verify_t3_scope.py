"""Tier 3 端到端等价性验证: scope_resolver 作为行级唯一真相源.

对照原 DataPermissionRule ROW 镜像 (unit_ids_to_dept_ids + collect_unit_member_users)
证明 scope_filter_q 对「管理单元范围用户」产出的过滤 Q 与旧镜像完全一致。

用法:
  cd apps/django
  .venv/bin/python scripts/verify_t3_scope.py
"""
import os
import sys

# 把 apps/django 加入路径, 使 config / apps 可被 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
try:
    django.setup()
except Exception as e:  # noqa: BLE001
    print(f'FAIL: Django 初始化失败 (检查 DATABASE_URL / .env): {e}')
    sys.exit(2)

from django.db import transaction

from apps.core.models import Department, User
from apps.core.models_permission_v2 import ManagementUnit, UserRoleV2
from apps.candidate.models import Candidate
from apps.core.scope_resolver import (
    scope_filter_q, unit_ids_to_dept_ids, collect_unit_member_users,
)
from django.db.models import Q


PREFIX = 'T3E2E_'


def _cleanup():
    Candidate.objects.filter(name__startswith=PREFIX).delete()
    UserRoleV2.objects.filter(role_code__startswith=PREFIX).delete()
    ManagementUnit.objects.filter(unit_name__startswith=PREFIX).delete()
    User.objects.filter(username__startswith=PREFIX).delete()
    Department.objects.filter(id__startswith=PREFIX).delete()


def main():
    ok = True
    msgs = []
    try:
        with transaction.atomic():
            # 1) 部门: 一个在管理单元范围内, 一个在范围外
            dept_in = Department.objects.create(
                id=f'{PREFIX}DEPT_IN', name=f'{PREFIX}部门内', code=f'{PREFIX}DEPT_IN',
                path=f'/{PREFIX}DEPT_IN', is_active=True,
            )
            dept_out = Department.objects.create(
                id=f'{PREFIX}DEPT_OUT', name=f'{PREFIX}部门外', code=f'{PREFIX}DEPT_OUT',
                path=f'/{PREFIX}DEPT_OUT', is_active=True,
            )

            # 2) 推荐人 (参考人): 一个在范围内部门, 一个在范围外
            ref_in = User.objects.create_user(
                username=f'{PREFIX}ref_in', password='x', department=dept_in)
            ref_out = User.objects.create_user(
                username=f'{PREFIX}ref_out', password='x', department=dept_out)

            # 3) 管理单元: org_scope 映射到 dept_in
            unit = ManagementUnit.objects.create(
                unit_name=f'{PREFIX}单元', system_code='recruit', unit_type='org',
                org_scope=[dept_in.id], status=1,
            )

            # 4) 被测用户: 持有该管理单元 (per-app recruit)
            u = User.objects.create_user(username=f'{PREFIX}user', password='x')
            UserRoleV2.objects.create(
                user_id=u.pk, role_code=f'{PREFIX}R', system_code='recruit',
                app_data_scopes={'recruit': [unit.id]}, granted_by_id=1,
            )

            # 5) 候选人: 一个 referrer 在范围内, 一个在范围外
            c_in = Candidate.objects.create(
                name=f'{PREFIX}in', phone=f'1300000000{PREFIX[-1]}',
                current_state='APPLIED', referrer=ref_in, created_by=u,
            )
            c_out = Candidate.objects.create(
                name=f'{PREFIX}out', phone=f'1300000001{PREFIX[-1]}',
                current_state='APPLIED', referrer=ref_out, created_by=u,
            )

            # 6) 调用 scope_filter_q (与 CandidateViewSet 相同入参)
            q = scope_filter_q(
                u, app_code='recruit',
                scope_field='referrer__department', creator_field='created_by',
            )
            got_ids = set(Candidate.objects.filter(q).values_list('id', flat=True))

            expected = {c_in.id}
            if got_ids == expected:
                msgs.append(f'PASS: scope_filter_q 精确过滤到范围内候选人 {sorted(expected)}')
            else:
                ok = False
                msgs.append(f'FAIL: 期望 {sorted(expected)}, 实际 {sorted(got_ids)}')

            # 7) 等价性对照: 旧镜像 helper 解析结果
            dept_ids = unit_ids_to_dept_ids([unit.id])
            user_ids = collect_unit_member_users([unit.id])
            msgs.append(f'INFO: unit_ids_to_dept_ids={dept_ids}, collect_unit_member_users={user_ids}')
            if dept_ids != [dept_in.id]:
                ok = False
                msgs.append(f'FAIL: org_scope 解析部门不一致: {dept_ids}')

            # 8) 对照: 直接用旧 CUSTOM 镜像的 Q 形状 (无成员时只按部门), 应与 scope_filter_q 同效
            legacy_q = Q(**{'referrer__department__in': dept_ids})
            legacy_ids = set(Candidate.objects.filter(legacy_q).values_list('id', flat=True))
            if legacy_ids == expected:
                msgs.append('PASS: 与旧镜像 CUSTOM Q 形状一致')
            else:
                ok = False
                msgs.append(f'FAIL: 旧镜像对照不一致: {sorted(legacy_ids)}')

            # 回滚测试数据, 不污染 dev DB
            transaction.set_rollback(True)
    except Exception as e:  # noqa: BLE001
        ok = False
        msgs.append(f'FAIL: 异常 {type(e).__name__}: {e}')

    print('\n'.join(msgs))
    print('RESULT: ' + ('PASS' if ok else 'FAIL'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
