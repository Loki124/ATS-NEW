"""M06 可见范围预览 / 零命中引导 / 管理单元完整度测试。

核心断言：preview_entity_scope 与列表同源（直接调 scope_filter_q），
其 raw 必须等于 scope_filter_q 的字符串——证明「预览所见即列表所得」，无二次实现漂移。
"""
from django.db.models import Q
from django.test import TestCase

from apps.core.models import Department, User
from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.core.scope_preview import (
    describe_scope_q,
    diagnose_zero_hits,
    management_unit_completeness,
    preview_entity_scope,
)
from apps.core.scope_resolver import scope_filter_q


class ScopePreviewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Department.objects.create(id='D1', name='华东大区')
        cls.u = User.objects.create(username='u_preview', department_id='D1')
        cls.u_admin = User.objects.create(username='u_preview_admin', is_superuser=True, department_id='D1')

    # --- 同源保证（最关键）---

    def test_preview_same_source_as_list(self):
        # 列表 get_queryset 调 scope_filter_q；预览必须产出完全一致的 Q 字符串
        q = scope_filter_q(self.u, entity='candidate')
        desc = preview_entity_scope(self.u, 'candidate')
        self.assertEqual(desc['raw'], str(q))

    def test_super_admin_sees_all(self):
        desc = preview_entity_scope(self.u_admin, 'candidate')
        self.assertTrue(desc['is_super_admin'])
        self.assertTrue(desc['all_data'])
        # 超管无行级限制
        self.assertFalse(desc['department_ids'])
        self.assertFalse(desc['user_ids'])

    def test_no_scope_user_is_self_only(self):
        # 无管理单元/角色 -> scope_filter_q 回退 SELF -> 预览标 self_only
        desc = preview_entity_scope(self.u, 'candidate')
        self.assertTrue(desc['self_only'])
        self.assertIn(self.u.pk, desc['user_ids'])

    # --- describe_scope_q ---

    def test_describe_department_in(self):
        q = Q(department_id__in=['D1', 'D2'])
        d = describe_scope_q(q)
        self.assertCountEqual(d['department_ids'], ['D1', 'D2'])
        self.assertFalse(d['self_only'])

    def test_describe_empty_pk(self):
        d = describe_scope_q(Q(pk__in=[]))
        self.assertTrue(d['empty'])

    def test_describe_recruit_type_partition(self):
        q = Q(recruit_type='campus') & Q(created_by=self.u.pk)
        d = describe_scope_q(q)
        self.assertEqual(d['recruit_type'], 'campus')
        self.assertTrue(d['self_only'])

    # --- diagnose_zero_hits ---

    def test_diagnose_empty(self):
        hints = diagnose_zero_hits({'empty': True})
        self.assertTrue(any('可见范围为空' in h for h in hints))

    def test_diagnose_self_only(self):
        hints = diagnose_zero_hits({'self_only': True})
        self.assertTrue(any('自己创建' in h for h in hints))

    def test_diagnose_custom_replaced(self):
        hints = diagnose_zero_hits({'custom_replaced': True})
        self.assertTrue(any('角色自定义' in h for h in hints))

    def test_diagnose_fallback(self):
        hints = diagnose_zero_hits({})
        self.assertTrue(hints)  # 至少一条兜底提示

    # --- management_unit_completeness ---

    def test_unit_completeness_flags_incomplete(self):
        # 无 org_scope / 无成员 -> incomplete
        from apps.core.models_permission_v2 import ManagementUnit
        unit = ManagementUnit.objects.create(unit_name='空单元', status=1)
        res = management_unit_completeness([unit.id])
        self.assertIn(unit.id, res)
        self.assertFalse(res[unit.id]['complete'])
        self.assertFalse(res[unit.id]['has_org_scope'])

    def test_unit_completeness_with_org_scope(self):
        from apps.core.models_permission_v2 import ManagementUnit
        unit = ManagementUnit.objects.create(
            unit_name='有范围单元', status=1, org_scope={'departments': ['D1']},
        )
        res = management_unit_completeness([unit.id])
        self.assertTrue(res[unit.id]['complete'])
        self.assertTrue(res[unit.id]['has_org_scope'])
