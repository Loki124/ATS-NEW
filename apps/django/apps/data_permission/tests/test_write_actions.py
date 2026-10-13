"""权限 v2 动作粒度测试（需要 DB）。

docs/plan-read-write-action-permission.md §3.4 动作级 fail-closed：
- 配置写范围后，未授权的动作一律拒绝（**不许回落功能权限** —— 防
  「只配 ['edit'] 后 delete 因无规则包含它而被 fail-open 放行」的反向放大漏洞）；
- 只有授权了当前动作的规则才贡献范围（范围不跨动作串用）；
- 停用动作一律拒绝（安全方向）；
- actions=NULL = 全动作放行（双读兼容，存量 WRITE 规则语义不变）；
- 无 WRITE 规则 = fail-open（opt-in 现状不变）。

字典表种子由迁移 0006 灌入（test DB 跑全量迁移，种子天然就绪）。
"""
from django.test import TestCase

from apps.candidate.models import Candidate
from apps.core.models import Department, User
from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.data_permission import action_registry
from apps.data_permission.action_map import ACTION_REGISTRY, sync_seed
from apps.data_permission.enforcement import is_writable, write_scope_q
from apps.data_permission.models import (
    DataPermissionAction,
    DataPermissionRule,
    RowScopeAccess,
    RowScopeType,
)


class WriteActionScopeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Department.objects.create(id='D1', name='华东大区')
        Department.objects.create(id='D2', name='华南大区')

        cls.u_rule = User.objects.create(username='u_act', department_id='D1')
        cls.u_d2 = User.objects.create(username='u_act_d2', department_id='D2')

        RoleV2.objects.create(system_code='recruit', role_code='ACT_ROLE', role_name='动作测试', status=1)
        UserRoleV2.objects.create(user_id=cls.u_rule.pk, role_code='ACT_ROLE', system_code='recruit')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 用例间字典缓存隔离（test settings 已置 TTL=0，此处双保险）
        action_registry.invalidate_cache()

    def setUp(self):
        action_registry.invalidate_cache()

    def _make_write_rule(self, scope_type=RowScopeType.ALL, payload=None, actions=None):
        return DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value='ACT_ROLE', level='ROW',
            row_access=RowScopeAccess.WRITE, entity='candidate',
            scope_type=scope_type, scope_payload=payload, actions=actions, status=1,
        )

    def _candidate(self, dept_id='D1', n=0):
        # candidate 的 dept 维度是 referrer__department_id（见 field_map.MODULE_DIMENSION_FIELDS），
        # 故用 referrer 的部门控制候选人归属部门（与 test_write_scope 同款）。
        referrer = self.u_rule if dept_id == 'D1' else self.u_d2
        return Candidate.objects.create(
            name=f'ca{n}', phone=f'1390000{n:04d}', referrer=referrer,
        )

    # --- fail-closed 核心：未授权动作一律拒绝 ---

    def test_unlisted_action_denied_not_fail_open(self):
        """配了 actions=['edit'] 后 delete 必须被拒（反向放大漏洞回归锚点）。"""
        self._make_write_rule(RowScopeType.ALL, actions=['edit'])
        c = self._candidate(n=1)
        self.assertTrue(is_writable(self.u_rule, 'candidate', c, action='edit'))
        # delete 未被任何规则授权 -> 拒绝（Q(pk__in=[])），绝不回落功能权限
        q = write_scope_q(self.u_rule, 'candidate', action='delete')
        self.assertIsNotNone(q)
        self.assertFalse(is_writable(self.u_rule, 'candidate', c, action='delete'))

    def test_actions_null_allows_all_actions(self):
        """actions=NULL = 全动作放行（存量 WRITE 规则双读兼容）。"""
        self._make_write_rule(RowScopeType.ALL, actions=None)
        c = self._candidate(n=2)
        self.assertTrue(is_writable(self.u_rule, 'candidate', c, action='edit'))
        self.assertTrue(is_writable(self.u_rule, 'candidate', c, action='delete'))
        self.assertTrue(is_writable(self.u_rule, 'candidate', c, action='eliminate'))

    def test_scope_not_shared_across_actions(self):
        """范围不跨动作串用：edit 的范围只来自授权 edit 的规则。"""
        custom = {'expr': '1', 'groups': [{'expr': '1', 'conditions': [
            {'dimension': 'dept', 'operator': 'in',
             'values': [{'id': 'D1', 'label': '华东'}]},
        ]}]}
        other = {'expr': '1', 'groups': [{'expr': '1', 'conditions': [
            {'dimension': 'dept', 'operator': 'in',
             'values': [{'id': 'D2', 'label': '华南'}]},
        ]}]}
        self._make_write_rule(RowScopeType.CUSTOM, payload=custom, actions=['edit'])
        self._make_write_rule(RowScopeType.CUSTOM, payload=other, actions=['delete'])
        in_d1 = self._candidate(dept_id='D1', n=3)
        in_d2 = self._candidate(dept_id='D2', n=4)
        # edit 只看 D1（来自 edit 规则），不混入 delete 规则的 D2
        self.assertTrue(is_writable(self.u_rule, 'candidate', in_d1, action='edit'))
        self.assertFalse(is_writable(self.u_rule, 'candidate', in_d2, action='edit'))
        # delete 只看 D2
        self.assertTrue(is_writable(self.u_rule, 'candidate', in_d2, action='delete'))
        self.assertFalse(is_writable(self.u_rule, 'candidate', in_d1, action='delete'))
        # transition 无人授权 -> 拒绝
        self.assertFalse(is_writable(self.u_rule, 'candidate', in_d1, action='transition'))

    # --- 停用动作一律拒绝 ---

    def test_disabled_action_denied_even_if_authorized(self):
        self._make_write_rule(RowScopeType.ALL, actions=['edit', 'delete'])
        DataPermissionAction.objects.filter(pk='delete').update(enabled=False)
        action_registry.invalidate_cache()
        c = self._candidate(n=5)
        self.assertTrue(is_writable(self.u_rule, 'candidate', c, action='edit'))
        self.assertFalse(is_writable(self.u_rule, 'candidate', c, action='delete'))

    # --- opt-in fail-open 不变 ---

    def test_no_write_rule_still_fail_open_with_action(self):
        """无 WRITE 规则 -> None -> 沿用功能权限（任何动作都不额外限制）。"""
        self.assertIsNone(write_scope_q(self.u_rule, 'candidate', action='delete'))
        self.assertIsNone(write_scope_q(self.u_rule, 'candidate', action='eliminate'))

    def test_new_wired_actions_registered(self):
        """v2 新增的 4 个兵哥点名动作必须在种子注册表中（接线前提）。"""
        for key in ('recommend', 'eliminate', 'talent_pool_add', 'notify'):
            self.assertIn(key, action_registry.enabled_action_keys(), key)

    # --- validate_write_actions（保存期校验）---

    def test_validate_write_actions(self):
        self.assertIsNone(action_registry.validate_write_actions(None))
        self.assertIsNone(action_registry.validate_write_actions(['edit', 'transition']))
        self.assertIsNotNone(action_registry.validate_write_actions(['no_such_action']))
        self.assertIsNotNone(action_registry.validate_write_actions('edit'))  # 非数组
        self.assertIsNotNone(action_registry.validate_write_actions([None]))
        # 停用动作不允许再配进新规则
        DataPermissionAction.objects.filter(pk='merge').update(enabled=False)
        action_registry.invalidate_cache()
        self.assertIsNotNone(action_registry.validate_write_actions(['merge']))


class SyncSeedTestCase(TestCase):
    """sync_seed 幂等性 + 自定义动作保护。"""

    def test_sync_seed_idempotent(self):
        # 注意：test DB 建库时迁移 0006 已灌过种子，故首次 created 可能为 0；
        # 幂等性本身才是断言目标 —— 连续调用不产生任何新增/更新。
        sync_seed()
        second = sync_seed()
        self.assertEqual(second['created'], 0)
        self.assertEqual(second['updated'], 0)
        # 全部种子动作就位、系统属性、启用
        for key in ACTION_REGISTRY:
            obj = DataPermissionAction.objects.get(pk=key)
            self.assertTrue(obj.is_system, key)
            self.assertTrue(obj.enabled, key)

    def test_custom_action_survives_sync(self):
        sync_seed()
        DataPermissionAction.objects.create(
            key='custom_mark_star', label='标星', category='write', is_system=False,
        )
        result = sync_seed()
        obj = DataPermissionAction.objects.get(pk='custom_mark_star')
        self.assertTrue(obj.enabled)
        self.assertFalse(obj.is_system)
        # 自定义动作不计入种子的 updated（种子只回填 is_system 行）
        self.assertNotIn('custom_mark_star', DataPermissionAction.objects.filter(
            is_system=True).values_list('key', flat=True))

    def test_removed_seed_action_gets_disabled_not_deleted(self):
        sync_seed()
        # 模拟「种子移除了某系统动作」：直接改库中 key 再跑 sync（不移除行）
        DataPermissionAction.objects.create(
            key='legacy_action', label='遗留', category='write', is_system=True, enabled=True,
        )
        sync_seed()
        obj = DataPermissionAction.objects.get(pk='legacy_action')
        self.assertFalse(obj.enabled)   # 停用而非删除（可能被规则引用）
        self.assertTrue(DataPermissionAction.objects.filter(pk='legacy_action').exists())
