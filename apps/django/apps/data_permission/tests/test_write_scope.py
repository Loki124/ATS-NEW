"""M07 写范围 enforcement 测试（需要 DB）。

验证：write_scope_q / is_writable / ensure_writable / filter_writable 与读范围 role_entity_scope_q
对称，但仅认 row_access=WRITE 规则，且支持 OWNER 写范围（候选 -> referrer）。
opt-in 安全默认：无 WRITE 规则 -> 写范围 None -> 沿用既有功能权限（不锁死写入口）。
"""
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.test import TestCase

from apps.candidate.models import Candidate
from apps.core.models import Department, User
from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.data_permission.enforcement import (
    ensure_writable,
    filter_writable,
    is_writable,
    write_scope_q,
)
from apps.data_permission.models import DataPermissionRule, RowScopeAccess, RowScopeType


class WriteScopeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Department.objects.create(id='D1', name='华东大区')
        Department.objects.create(id='D2', name='华南大区')

        cls.u_rule = User.objects.create(username='u_rule', department_id='D1')
        cls.u_other = User.objects.create(username='u_other', department_id='D2')
        cls.u_admin = User.objects.create(username='u_admin', is_superuser=True, department_id='D1')

        RoleV2.objects.create(system_code='recruit', role_code='TEST_ROLE', role_name='测试', status=1)
        UserRoleV2.objects.create(user_id=cls.u_rule.pk, role_code='TEST_ROLE', system_code='recruit')

    def _make_write_rule(self, scope_type, payload=None):
        return DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value='TEST_ROLE', level='ROW',
            row_access=RowScopeAccess.WRITE, entity='candidate',
            scope_type=scope_type, scope_payload=payload, status=1,
        )

    def _candidate(self, referrer=None, n=0):
        return Candidate.objects.create(
            name=f'c{n}', phone=f'1380000{n:04d}',
            referrer=referrer,
        )

    # --- opt-in 安全默认 ---

    def test_no_write_rule_is_none_and_allows(self):
        # 无 WRITE 规则 -> 写范围 None -> is_writable True（沿用既有功能权限, fail-open）
        self.assertIsNone(write_scope_q(self.u_rule, 'candidate'))
        c = self._candidate(referrer=self.u_other, n=1)
        self.assertTrue(is_writable(self.u_rule, 'candidate', c, action='edit'))

    def test_super_admin_no_write_restriction(self):
        self.assertIsNone(write_scope_q(self.u_admin, 'candidate'))

    # --- OWNER 写范围 ---

    def test_owner_allows_only_owner(self):
        self._make_write_rule(RowScopeType.OWNER)
        mine = self._candidate(referrer=self.u_rule, n=2)
        others = self._candidate(referrer=self.u_other, n=3)
        self.assertTrue(is_writable(self.u_rule, 'candidate', mine, action='edit'))
        self.assertFalse(is_writable(self.u_rule, 'candidate', others, action='edit'))

    def test_owner_scope_q_uses_referrer(self):
        self._make_write_rule(RowScopeType.OWNER)
        q = write_scope_q(self.u_rule, 'candidate')
        self.assertIsNotNone(q)
        self.assertIn('referrer', str(q))
        self.assertIn(str(self.u_rule.pk), str(q))

    # --- ALL / NONE ---

    def test_all_scope_allows_any(self):
        self._make_write_rule(RowScopeType.ALL)
        c = self._candidate(referrer=self.u_other, n=4)
        self.assertTrue(is_writable(self.u_rule, 'candidate', c, action='edit'))

    def test_none_scope_allows_none(self):
        self._make_write_rule(RowScopeType.NONE)
        c = self._candidate(referrer=self.u_rule, n=5)
        self.assertFalse(is_writable(self.u_rule, 'candidate', c, action='edit'))

    # --- ensure_writable 抛错语义 ---

    def test_ensure_writable_raises_on_violation(self):
        self._make_write_rule(RowScopeType.OWNER)
        others = self._candidate(referrer=self.u_other, n=6)
        with self.assertRaises(PermissionDenied):
            ensure_writable(self.u_rule, 'candidate', others, action='edit')

    def test_ensure_writable_passes_for_owner(self):
        self._make_write_rule(RowScopeType.OWNER)
        mine = self._candidate(referrer=self.u_rule, n=7)
        # 不抛
        ensure_writable(self.u_rule, 'candidate', mine, action='edit')

    def test_ensure_writable_failopen_without_rule(self):
        # 无 WRITE 规则 -> 不抛
        c = self._candidate(referrer=self.u_other, n=8)
        ensure_writable(self.u_rule, 'candidate', c, action='edit')

    # --- filter_writable ---

    def test_filter_writable_restricts_queryset(self):
        self._make_write_rule(RowScopeType.OWNER)
        mine = self._candidate(referrer=self.u_rule, n=9)
        others = self._candidate(referrer=self.u_other, n=10)
        qs = Candidate.objects.filter(pk__in=[mine.pk, others.pk])
        filtered = filter_writable(self.u_rule, 'candidate', qs, action='edit')
        self.assertEqual(set(filtered.values_list('pk', flat=True)), {mine.pk})

    # --- 非法 action 早失败 ---

    def test_invalid_action_raises(self):
        with self.assertRaises(Exception):
            write_scope_q(self.u_rule, 'candidate', action='not_a_real_action')

    # --- 读规则不影响写范围（双读兼容）---

    def test_read_rule_does_not_affect_write_scope(self):
        # 仅配 READ 规则 -> 写范围仍 None（不误拦截写入口）
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value='TEST_ROLE', level='ROW',
            row_access=RowScopeAccess.READ, entity='candidate',
            scope_type=RowScopeType.OWNER, status=1,
        )
        self.assertIsNone(write_scope_q(self.u_rule, 'candidate'))
        c = self._candidate(referrer=self.u_other, n=11)
        self.assertTrue(is_writable(self.u_rule, 'candidate', c, action='edit'))
