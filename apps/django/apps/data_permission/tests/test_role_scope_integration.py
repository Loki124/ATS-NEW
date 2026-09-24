"""角色自定义范围 enforcement 集成测试（需要 DB）。

验证：role_entity_scope_q 把角色的 CUSTOM 表达式规则编译成正确的 Q，
scope_filter_q(entity=...) 在有配置时优先返回自定义 Q（替换默认 scope）。
"""
from django.db.models import Q
from django.test import TestCase

from apps.core.models import Department, User
from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.core.role_v2_query import is_super_admin
from apps.core.scope_resolver import scope_filter_q
from apps.data_permission.enforcement import role_entity_scope_q
from apps.data_permission.models import DataPermissionRule


class RoleScopeIntegrationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Department.objects.create(id='D1', name='华东大区')
        Department.objects.create(id='D2', name='华南大区')

        cls.u_rule = User.objects.create(username='u_rule', department_id='D1')
        cls.u_other = User.objects.create(username='u_other', department_id='D2')
        cls.u_admin = User.objects.create(username='u_admin', is_superuser=True, department_id='D1')

        RoleV2.objects.create(system_code='recruit', role_code='TEST_ROLE', role_name='测试', status=1)
        UserRoleV2.objects.create(user_id=cls.u_rule.pk, role_code='TEST_ROLE', system_code='recruit')

        # 角色 TEST_ROLE 在 candidate 模块配置 CUSTOM：部门 属于 [D1]
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value='TEST_ROLE', level='ROW',
            entity='candidate', scope_type='CUSTOM',
            scope_payload={'expr': '1', 'groups': [{
                'expr': '1',
                'conditions': [{'dimension': 'dept', 'operator': 'in', 'values': [{'id': 'D1'}]}],
            }]},
            status=1,
        )

    def test_role_entity_scope_q_compiles(self):
        q = role_entity_scope_q(self.u_rule, 'candidate')
        self.assertIsNotNone(q)
        s = str(q)
        self.assertIn('referrer__department_id', s)
        self.assertIn('D1', s)

    def test_scope_filter_q_uses_custom_when_configured(self):
        q = scope_filter_q(self.u_rule, entity='candidate')
        self.assertIsNotNone(q)
        self.assertIn('referrer__department_id', str(q))

    def test_no_rule_falls_back_to_none(self):
        # u_other 没有 TEST_ROLE -> 无自定义规则 -> None（调用方回退默认 scope）
        self.assertIsNone(role_entity_scope_q(self.u_other, 'candidate'))

    def test_super_admin_no_custom(self):
        self.assertTrue(is_super_admin(self.u_admin))
        self.assertIsNone(role_entity_scope_q(self.u_admin, 'candidate'))

    def test_mode_none_produces_empty_set(self):
        # 同一角色在 talent 模块配 NONE -> 看不到数据
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value='TEST_ROLE', level='ROW',
            entity='talent', scope_type='NONE', status=1,
        )
        q = role_entity_scope_q(self.u_rule, 'talent')
        self.assertIsNotNone(q)
        self.assertIn('pk__in', str(q))

    def test_mode_all_produces_full(self):
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value='TEST_ROLE', level='ROW',
            entity='position', scope_type='ALL', status=1,
        )
        q = role_entity_scope_q(self.u_rule, 'position')
        # ALL -> Q() (空 Q 表示全量)
        self.assertEqual(q, Q())
