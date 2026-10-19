"""动态策略(Dynamic Strategy) 后端运行时语义测试.

覆盖三项核心契约:
1. /me 功能权限并集: 指派且启用的策略所授予的资源码并入 permissions.
2. strategy_write_scope 多策略合并: 动作并集 + mode 优先级 scope>owner>all>none.
3. 未被任何策略管辖的模块 -> 返回 None (回退既有 role 级写范围逻辑).
"""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Department, User
from apps.core.models_permission_v2 import (
    DynamicStrategy,
    DynamicStrategyAssignment,
    RoleV2,
    UserRoleV2,
)
from apps.data_permission.enforcement import strategy_write_scope


class DynamicStrategyScopeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_code = 'DS_TEST_ROLE'
        RoleV2.objects.create(
            system_code='recruit', role_code=cls.role_code,
            role_name='动态策略测试角色', status=1,
        )
        cls.dept, _ = Department.objects.get_or_create(
            id='DS_TEST_DEPT', defaults={'name': '动态策略测试部门'})
        cls.user = User.objects.create(username='ds_test_user', department=cls.dept)
        UserRoleV2.objects.create(
            user_id=cls.user.pk, role_code=cls.role_code, system_code='recruit')

    def _strategy(self, code, governed, granted, module_config, status=1):
        return DynamicStrategy.objects.create(
            system_code='recruit', strategy_code=code,
            strategy_name=code, status=status,
            governed_functions=governed,
            granted_resource_codes=granted,
            module_config=module_config,
        )

    def _assign(self, strategy_code):
        DynamicStrategyAssignment.objects.create(
            system_code='recruit', strategy_code=strategy_code,
            role_code=self.role_code)

    # ------------------------------------------------------------------
    # 1. /me 并集
    # ------------------------------------------------------------------
    def test_me_union_adds_granted_codes(self):
        """指派的启用策略其授予码应并入 /me 的 permissions."""
        self._strategy(
            'DS_UNION', ['candidate'], ['recruit:candidate:export'], {}, status=1)
        self._assign('DS_UNION')

        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.get('/api/v1/auth/me/')
        self.assertEqual(resp.status_code, 200)
        perms = resp.data['data']['permissions']
        self.assertIn('recruit:candidate:export', perms)

    def test_me_union_skips_disabled_strategy(self):
        """禁用(status=0)的策略不参与并集."""
        self._strategy(
            'DS_OFF', ['candidate'], ['recruit:candidate:export'], {}, status=0)
        self._assign('DS_OFF')

        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.get('/api/v1/auth/me/')
        perms = resp.data['data']['permissions']
        self.assertNotIn('recruit:candidate:export', perms)

    # ------------------------------------------------------------------
    # 2. strategy_write_scope 合并
    # ------------------------------------------------------------------
    def test_strategy_write_scope_merges_multiple(self):
        """多策略合并: 动作并集 + mode 优先级 scope>owner>all>none."""
        # A: scope 模式, 动作 edit
        self._strategy(
            'DS_A', ['candidate'], [],
            {'candidate': {'mode': 'scope', 'actions': ['edit'], 'groups': [], 'expr': ''}})
        # B: owner 模式, 动作 delete
        self._strategy(
            'DS_B', ['candidate'], [],
            {'candidate': {'mode': 'owner', 'actions': ['delete'], 'groups': [], 'expr': ''}})
        self._assign('DS_A')
        self._assign('DS_B')

        result = strategy_write_scope(self.user, 'candidate')
        self.assertIsNotNone(result)
        mode, actions = result
        # scope > owner -> scope
        self.assertEqual(mode, 'scope')
        # 动作并集 + 排序
        self.assertEqual(actions, ['delete', 'edit'])

    def test_strategy_write_scope_owner_beats_all(self):
        """owner 优先于 all."""
        self._strategy(
            'DS_C', ['candidate'], [],
            {'candidate': {'mode': 'all', 'actions': ['edit'], 'groups': [], 'expr': ''}})
        self._strategy(
            'DS_D', ['candidate'], [],
            {'candidate': {'mode': 'owner', 'actions': ['edit'], 'groups': [], 'expr': ''}})
        self._assign('DS_C')
        self._assign('DS_D')
        mode, _ = strategy_write_scope(self.user, 'candidate')
        self.assertEqual(mode, 'owner')

    # ------------------------------------------------------------------
    # 3. 未管辖 -> 回退 None
    # ------------------------------------------------------------------
    def test_strategy_write_scope_none_when_not_governed(self):
        """模块未被任何策略管辖 -> None (回退既有 role 级逻辑)."""
        self._strategy(
            'DS_E', ['candidate'], [],
            {'candidate': {'mode': 'all', 'actions': [], 'groups': [], 'expr': ''}})
        self._assign('DS_E')
        # 'position' 未被任何策略管辖
        self.assertIsNone(strategy_write_scope(self.user, 'position'))

    def test_strategy_write_scope_none_for_unassigned_user(self):
        """无策略指派的用户 -> None."""
        self._strategy(
            'DS_F', ['candidate'], [],
            {'candidate': {'mode': 'all', 'actions': [], 'groups': [], 'expr': ''}})
        # 不指派给当前用户
        self.assertIsNone(strategy_write_scope(self.user, 'candidate'))

    # ------------------------------------------------------------------
    # 4. 迁移 0034 授予 ADMIN 角色的动态策略资源码
    # ------------------------------------------------------------------
    def test_migration_0034_grants_admin_dynamic_strategy_codes(self):
        """迁移 0034 给 ADMIN 角色写入 5 条 recruit:dynamic_strategy:* 授权行,
        ADMIN 用户经 /me 应能在 permissions 中看到这些码 (验证资源码缺失修复端到端生效)."""
        # 测试库由迁移构建, 不一定含 RoleV2 行; 角色码为纯字符串, 建一条以贴近真实.
        RoleV2.objects.get_or_create(
            system_code='recruit', role_code='ADMIN',
            defaults={'role_name': '管理员', 'status': 1})
        admin_user = User.objects.create(username='ds_admin_user', department=self.dept)
        UserRoleV2.objects.create(
            user_id=admin_user.pk, role_code='ADMIN', system_code='recruit')

        client = APIClient()
        client.force_authenticate(user=admin_user)
        resp = client.get('/api/v1/auth/me/')
        self.assertEqual(resp.status_code, 200)
        perms = resp.data['data']['permissions']
        for code in (
            'recruit:dynamic_strategy:menu:view',
            'recruit:dynamic_strategy:list',
            'recruit:dynamic_strategy:create',
            'recruit:dynamic_strategy:edit',
            'recruit:dynamic_strategy:delete',
        ):
            self.assertIn(code, perms)
