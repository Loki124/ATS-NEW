"""卡 1.2「未配置」显式态 + 卡 1.3 featureGranted 真实接线（需要 DB）。

## 为什么要有这组测试

### 卡 1.2：unset 与 none 语义相反，合并即出安全事故
历史上「从未配置过」（无规则行）与「显式配置为全部」（scope_type=ALL）
在上报时被合并成mode='all'，管理员无法区分「我配的」与「根本没配」。
本次把二者显式拆开：新增 mode='unset'，落库行为= **删除读行**。
而 mode='none'（无权限）落库行为= **新建/保留一行 scope_type=NONE**。
两者落库动作完全相反，半年后必有人试图合并 —— 本文件第3 条用例
（unset 真删行）就是那道防线：**删行不生效时它必须红**。

### 卡 1.3：featureGranted 曾是恒 True 硬编码
前端旧口径 `lower.includes('.' + k + '.')` 在 seed 全部 275 条资源码上
**恒 false**（资源码全是冒号分隔，无一条含点号），且工单原文给的
`process -> application` 映射与 process 的真实资源
（`recruit:settings:recruitment_process:*`，module='settings'）不符，
照做会让真实管流程的角色被误判为未授予、process 卡直接禁用（管理员锁死）。
第 6 条用例专门锁「授 recruitment_process:edit 必须让 process 变 true」。
"""
from django.test import TestCase

from apps.core.models_permission_v2 import (
    PermissionResource,
    RolePermissionV2,
    RoleV2,
)
from apps.data_permission.models import DataPermissionRule
from apps.data_permission.role_scope_api import (
    UnsetWithWriteRowsError,
    build_modules_response,
    upsert_modules,
    validate_modules,
)

MODULE_KEYS = ['demand', 'process', 'position', 'candidate', 'talent']


class RoleScopeUnsetTestCase(TestCase):
    """unset 显式态（卡 1.2）"""

    @classmethod
    def setUpTestData(cls):
        cls.role = RoleV2.objects.create(
            system_code='recruit', role_code='TEST_UNSET_ROLE', role_name='未配置测试', status=1,
        )

    def _module(self, role, mk):
        return next(m for m in build_modules_response(role)['modules'] if m['moduleKey'] == mk)

    # ---- 用例 1：无任何规则 -> unset（不是 all）----
    def test_no_rule_returns_unset_not_all(self):
        """全新角色没有任何规则行时，5 模块全返回 mode='unset'。

        这是卡 1.2 的核心语义：'never configured' != 'configured as ALL'。
        若这里退回'all'，前端的「未配置」卡永远不出现，卡 1.2 整张白做。
        """
        for mk in MODULE_KEYS:
            self.assertEqual(self._module(self.role, mk)['mode'], 'unset', mk)

    def test_no_rule_returns_empty_expr_and_groups(self):
        m = self._module(self.role, 'demand')
        self.assertEqual(m['expr'], '')
        self.assertEqual(m['groups'], [])

    # ---- 用例 2：存量 scope_type=ALL 仍返回 'all' ----
    def test_existing_all_row_still_returns_all(self):
        """显式配了 scope_type=ALL 的存量行必须继续报'all'，绝不能被unset 吞掉。

        这条防的是另一个方向的回归：若把 ALL 也当成「未配置」，
        管理员明明配的「全部可见」会变成「走默认范围」（可能是只能看自己），
        权限被无声收紧 —— 比卡 1.2 要修的问题更严重。
        """
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value=self.role.role_code, level='ROW',
            entity='demand', scope_type='ALL', scope_payload=None, status=1,
        )
        self.assertEqual(self._module(self.role, 'demand')['mode'], 'all')
        # 同一次响应里其它模块仍是 unset —— 证明不是全局替换
        self.assertEqual(self._module(self.role, 'candidate')['mode'], 'unset')

    # ---- 用例 3：unset 真的删掉读行（最重要的防假绿用例）----
    def test_unset_deletes_existing_custom_read_row(self):
        """先造 CUSTOM 读行 -> 下发 unset -> 保存 -> 规则真的消失。

        🔴 这条是本卡最重要的一条，直接验工单原文那个错方案：
        原方案说「unset 模块不下发（等价于无规则）」。但 upsert_modules 对
        **未被 payload 提及**的模块是「不动（差分的核心）」——
        不下发 -> 不进写入循环 -> 原CUSTOM 行原封不动 ->
        管理员把模块改回未配置后点保存，**什么都没发生且接口返回 200**。
        只有「显式下发 unset 且真的执行删除」才能让这个操作生效。
        """
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value=self.role.role_code, level='ROW',
            entity='candidate', scope_type='CUSTOM', status=1,
            scope_payload={'expr': '1', 'groups': [{
                'expr': '1',
                'conditions': [{'dimension': 'dept', 'operator': 'in', 'values': [{'id': 'D1'}]}],
            }]},
        )
        self.assertEqual(self._module(self.role, 'candidate')['mode'], 'scope')

        modules = [{'moduleKey': mk, 'mode': 'unset'} for mk in MODULE_KEYS]
        data = upsert_modules(self.role, modules, None)

        # 落库层面：读行确实不存在了（不是被改成 NONE）
        self.assertFalse(
            DataPermissionRule.objects.filter(
                dimension_type='ROLE', dimension_value=self.role.role_code,
                level='ROW', entity='candidate',
            ).exists(),
            'unset 后库里不应残留 candidate 规则行',
        )
        # 响应层面：回到 unset
        got = next(m for m in data['modules'] if m['moduleKey'] == 'candidate')
        self.assertEqual(got['mode'], 'unset')
        self.assertEqual(got['groups'], [])

    def test_unset_is_not_none(self):
        """unset 绝不能落成 scope_type=NONE —— 那等于把「未配置」变成「无权限」。

        对照：mode='none' 必须落出一行 NONE。这是同一组语义的另一半，
        两者一起断言才完整表达「unset 与 none 落库行为相反」这条铁律。
        """
        modules = [{'moduleKey': 'demand', 'mode': 'none'}]
        upsert_modules(self.role, modules, None)
        row = DataPermissionRule.objects.get(
            dimension_type='ROLE', dimension_value=self.role.role_code,
            level='ROW', entity='demand', row_access=None,
        )
        self.assertEqual(row.scope_type, 'NONE')

    def test_validate_accepts_unset_and_rejects_garbage(self):
        self.assertIsNone(validate_modules([{'moduleKey': 'demand', 'mode': 'unset'}]))
        reason = validate_modules([{'moduleKey': 'demand', 'mode': 'nope'}])
        self.assertIsNotNone(reason)
        self.assertIn('unset', reason)

    # ---- 用例 4：unset 遇存量 WRITE 行 -> 拒绝 ----
    def test_unset_rejected_when_write_row_exists(self):
        """存在存量 WRITE 行时下发 unset 必须被拒（fail-closed，产品已拍板）。

        理由：unset 语义是「该模块整体未配置」，而写范围独立存于 WRITE 行。
        悄悄放行会产出「读=未配置 + 写=有配置」的矛盾组合：界面无异常，
        但可见范围走默认、可写动作却仍被单独约束 —— 最难排查的权限错位。
        """
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value=self.role.role_code, level='ROW',
            entity='position', scope_type='ALL', row_access='WRITE',
            actions=['edit'], status=1,
        )
        modules = [{'moduleKey': 'position', 'mode': 'unset'}]
        with self.assertRaises(UnsetWithWriteRowsError) as ctx:
            upsert_modules(self.role, modules, None)
        msg = str(ctx.exception)
        # 文案必须能直接指导管理员下一步（说清是哪个模块 + 先做什么）
        self.assertIn('position', msg)
        self.assertIn('写范围', msg)

        # 关键：拒绝后该模块的 WRITE 行必须**原样还在**（事务回滚，无副作用）
        self.assertTrue(
            DataPermissionRule.objects.filter(
                dimension_type='ROLE', dimension_value=self.role.role_code,
                level='ROW', entity='position', row_access='WRITE',
            ).exists(),
            '拒绝保存后存量 WRITE 行不得被删除',
        )

    def test_unset_allowed_when_same_payload_clears_write(self):
        """同一次保存里先取消写范围（write.mode=none）再置 unset -> 合法放行。

        这条防的是把预检写成「只要有 WRITE 行就一律拒绝」—— 那会把一个
        本可以一次保存完成的动作（清写范围 + 置未配置）变成永远做不到的死路，
        管理员必须分两次保存，仍旧是被迫的绕路。
        """
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value=self.role.role_code, level='ROW',
            entity='talent', scope_type='ALL', row_access='WRITE',
            actions=['edit'], status=1,
        )
        modules = [{
            'moduleKey': 'talent', 'mode': 'unset',
            'write': {'mode': 'none', 'expr': '', 'groups': [], 'actions': []},
        }]
        data = upsert_modules(self.role, modules, None)
        self.assertFalse(
            DataPermissionRule.objects.filter(
                dimension_type='ROLE', dimension_value=self.role.role_code,
                level='ROW', entity='talent',
            ).exists(),
        )
        got = next(m for m in data['modules'] if m['moduleKey'] == 'talent')
        self.assertEqual(got['mode'], 'unset')


class FeatureGrantedTestCase(TestCase):
    """卡 1.3：featureGranted 按 PermissionResource.module 真实判定"""

    @classmethod
    def setUpTestData(cls):
        PermissionResource.objects.all().delete()
        RolePermissionV2.objects.all().delete()
        RoleV2.objects.all().delete()

        PermissionResource.objects.create(
            system_code='recruit', resource_code='recruit:candidate:list',
            resource_name='候选人列表', resource_type='BUTTON', module='candidate', status=1,
        )
        # process 的真实资源码：第二段是 settings（module='settings'），
        # 既不是 process 也不是 application —— 这正是不能用切段/别名口径的原因。
        PermissionResource.objects.create(
            system_code='recruit',
            resource_code='recruit:settings:recruitment_process:edit',
            resource_name='编辑招聘流程', resource_type='BUTTON', module='settings', status=1,
        )
        # 反例资源：application 实体与 process 无任何执行关联（全仓无 data_perm_entity 指向它）
        PermissionResource.objects.create(
            system_code='recruit', resource_code='recruit:application:edit',
            resource_name='推进申请', resource_type='BUTTON', module='application', status=1,
        )

        cls.role = RoleV2.objects.create(
            system_code='recruit', role_code='TEST_GRANT_ROLE', role_name='授权测试', status=1,
        )

    def _module(self, mk):
        return next(m for m in build_modules_response(self.role)['modules'] if m['moduleKey'] == mk)

    # ---- 用例 5：无对应资源 -> featureGranted=false ----
    def test_module_without_any_resource_is_not_granted(self):
        """角色没有任何 candidate 资源时，candidate 模块 featureGranted=false。"""
        self.assertIs(self._module('candidate')['featureGranted'], False)

    def test_other_modules_all_false_when_nothing_granted(self):
        """未授任何资源时 5 模块全 false —— 不再是无条件 True。"""
        for mk in MODULE_KEYS:
            self.assertIs(self._module(mk)['featureGranted'], False, mk)

    # ---- 用例 6：授 recruitment_process:edit -> process=true（防误禁用陷阱）----
    def test_process_granted_via_settings_module(self):
        """授 `recruit:settings:recruitment_process:edit` 时 process 必须 true。

        🔴 这条直接防工单原文方案（process -> application）造成的锁死事故：
        照原方案实现，真实管流程的角色 process 卡会被判为「未分配功能权限」
        而**禁用**，管理员既改不了也删不掉，只能去数据库手工救。
        """
        RolePermissionV2.objects.create(
            role_code=self.role.role_code, system_code='recruit',
            resource_code='recruit:settings:recruitment_process:edit',
        )
        self.assertIs(self._module('process')['featureGranted'], True)
        # 只影响 process，不波及其他模块
        self.assertIs(self._module('candidate')['featureGranted'], False)

    def test_application_resource_does_not_grant_process(self):
        """授 application 资源**不能**让 process 变true（反向锁定映射口径）。

        防止日后退而求其次改回 application 映射：两者无执行关联，
        授了 application 的角色并不管理招聘流程。
        """
        RolePermissionV2.objects.create(
            role_code=self.role.role_code, system_code='recruit',
            resource_code='recruit:application:edit',
        )
        self.assertIs(self._module('process')['featureGranted'], False)

    def test_candidate_granted_via_own_module(self):
        RolePermissionV2.objects.create(
            role_code=self.role.role_code, system_code='recruit',
            resource_code='recruit:candidate:list',
        )
        self.assertIs(self._module('candidate')['featureGranted'], True)

    def test_super_admin_always_granted(self):
        """超管恒 true：超管绕过角色资源分配，按资源判定会把超管全部卡置灰。"""
        sa = RoleV2.objects.create(
            system_code='recruit', role_code='SUPER_ADMIN', role_name='超管', status=1,
        )
        for m in build_modules_response(sa)['modules']:
            self.assertIs(m['featureGranted'], True, m['moduleKey'])

    def test_cross_system_permission_not_leaked(self):
        """同名 role_code 在别的 system 下的授权不得串到 recruit（system_code 过滤）。

        无此过滤时，别的系统里恰好存在同 role_code 且授了 candidate 资源的记录，
        会让本系统角色凭空获得功能权限 —— 权限放大，且极难察觉。
        """
        RolePermissionV2.objects.create(
            role_code=self.role.role_code, system_code='other_sys',
            resource_code='recruit:candidate:list',
        )
        self.assertIs(self._module('candidate')['featureGranted'], False)
