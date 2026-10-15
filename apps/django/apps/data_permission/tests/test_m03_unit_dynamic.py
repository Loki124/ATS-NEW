"""M03 单测：unit 复合维度编译 + dynamic user 值类型 + 保存校验维度适配 + options 空壳护栏。

覆盖 ARCH §3.3.2 的 unit 复合维度（静态 val / 动态 managedUnits / 空壳 fail-closed / 整公司哨兵）
与 dynamic user 值类型（owner/creator + currentUser.id），以及保存期校验的「维度 × 值类型」
适配规则（与编译期共用 DYNAMIC_DIMENSION_RULES，防口径分叉）。
"""
from django.db.models import Q
from django.test import TestCase

from apps.core.models import Department, User
from apps.core.models_permission_v2 import (
    ManagementUnit,
    ManagementUnitMember,
    UserRoleV2,
)
from apps.data_permission.expr_compiler import compile_scope_q, validate_scope_payload
from apps.data_permission.role_scope_api import _unit_options, options_payload
from apps.demand.models import Demand


def _mk_dept(name, parent=None):
    return Department.objects.create(name=name, parent=parent)


def _unit_payload(unit_ids, dynamic_key=None):
    """构造 unit 维度条件 payload。dynamic_key 非空 -> 动态形态，否则静态值列表。"""
    cond = {
        'kind': 'relationship',
        'dimension': 'unit',
        'operator': 'in',
    }
    if dynamic_key:
        cond['valueSource'] = 'dynamic'
        cond['dynamicKey'] = dynamic_key
    else:
        cond['valueSource'] = 'static'
        cond['values'] = [{'id': uid} for uid in unit_ids]
    return {'expr': '', 'groups': [{'expr': '', 'conditions': [cond]}]}


class UnitDimensionCompileTestCase(TestCase):
    """unit 复合维度编译：经 iter_unit_scopes 展开为「部门集合 ∪ 成员用户集合」。"""

    def setUp(self):
        self.root = _mk_dept('ROOT')
        self.bg = _mk_dept('智能BG', self.root)
        self.fe = _mk_dept('前端组', self.bg)
        self.be = _mk_dept('后端组', self.bg)

        # 普通单元：org_scope 指向智能BG（仅本级）
        self.u_org = ManagementUnit.objects.create(
            unit_name='U-ORG',
            org_scope=[{'deptId': str(self.bg.id), 'includeChildren': False}],
            include_children=0, status=1,
        )
        # 成员单元：仅以 前端组 为 DEPT 成员（无 org_scope）
        self.u_member = ManagementUnit.objects.create(
            unit_name='U-MEMBER', org_scope=[], include_children=0, status=1,
        )
        ManagementUnitMember.objects.create(
            unit=self.u_member, member_type='DEPT', department_id=str(self.fe.id),
            include_children=0, status=1,
        )
        # 空壳单元：无 org_scope 且无成员 -> 展开为空
        self.u_shell = ManagementUnit.objects.create(
            unit_name='U-SHELL', org_scope=None, status=1,
        )
        # 整公司哨兵单元
        self.u_all = ManagementUnit.objects.create(
            unit_name='U-ALL', org_scope={'type': 'ALL'}, status=1,
        )

    def test_unit_static_org_scope_expands(self):
        q = compile_scope_q(_unit_payload([self.u_org.id]), 'demand')
        s = str(q)
        self.assertIn('department_id', s)
        self.assertIn(str(self.bg.id), s)

    def test_unit_static_member_dept_expands(self):
        q = compile_scope_q(_unit_payload([self.u_member.id]), 'demand')
        s = str(q)
        self.assertIn('department_id', s)
        self.assertIn(str(self.fe.id), s)

    def test_unit_empty_shell_fails_closed(self):
        # 空壳单元展开为空 -> Q(pk__in=[]) -> 匹配不到任何行（不放行）
        q = compile_scope_q(_unit_payload([self.u_shell.id]), 'demand')
        self.assertEqual(Demand.objects.filter(q).count(), 0)

    def test_unit_all_sentinel_is_true(self):
        # 整公司哨兵 -> Q() 恒真
        q = compile_scope_q(_unit_payload([self.u_all.id]), 'demand')
        self.assertEqual(str(q), str(Q()))

    def test_unit_dynamic_managed_units_no_auth_fails_closed(self):
        # 用户无管理单元授权 -> 动态解析空集 -> fail-closed
        orphan = User.objects.create(username='m3-orphan')
        q = compile_scope_q(
            _unit_payload([], dynamic_key='currentUser.managedUnits'), 'demand', user=orphan,
        )
        self.assertEqual(Demand.objects.filter(q).count(), 0)

    def test_unit_dynamic_managed_units_expands(self):
        # 用户经 UserRoleV2 拥有 U-ORG 授权 -> 动态解析出该单元并展开
        u = User.objects.create(username='m3-user')
        UserRoleV2.objects.create(
            user_id=u.pk, role_code='r1', management_unit_ids=[self.u_org.id],
        )
        q = compile_scope_q(
            _unit_payload([], dynamic_key='currentUser.managedUnits'), 'demand', user=u,
        )
        s = str(q)
        self.assertIn('department_id', s)
        self.assertIn(str(self.bg.id), s)


class DynamicUserValueTypeTestCase(TestCase):
    """dynamic user 值类型：owner/creator 维度 + currentUser.id（标量 __in）。"""

    def setUp(self):
        self.bg = _mk_dept('BG')
        self.zhang = User.objects.create(username='zhang', department=self.bg)

    def _payload(self, dimension):
        return {'expr': '', 'groups': [{'expr': '', 'conditions': [{
            'kind': 'relationship', 'dimension': dimension, 'operator': 'in',
            'valueSource': 'dynamic', 'dynamicKey': 'currentUser.id',
        }]}]}

    def test_owner_current_user_id_compiles(self):
        # demand owner = hr_id，应编译为 Q(hr_id__in=[user.pk])
        q = compile_scope_q(self._payload('owner'), 'demand', user=self.zhang)
        s = str(q)
        self.assertIn('hr_id', s)
        self.assertIn(str(self.zhang.pk), s)

    def test_creator_current_user_id_compiles(self):
        # creator = created_by_id，应编译为 Q(created_by_id__in=[user.pk])
        q = compile_scope_q(self._payload('creator'), 'demand', user=self.zhang)
        s = str(q)
        self.assertIn('created_by_id', s)
        self.assertIn(str(self.zhang.pk), s)

    def test_owner_with_dept_source_fails_closed(self):
        # dept 值类型来源(currentUser.departments) 配 owner 维度 -> 维度不适配 -> fail-closed
        payload = {'expr': '', 'groups': [{'expr': '', 'conditions': [{
            'kind': 'relationship', 'dimension': 'owner', 'operator': 'in',
            'valueSource': 'dynamic', 'dynamicKey': 'currentUser.departments',
        }]}]}
        q = compile_scope_q(payload, 'demand', user=self.zhang)
        self.assertEqual(Demand.objects.filter(q).count(), 0)


class ValidateDimensionAdaptationTestCase(TestCase):
    """保存期校验：维度 × 值类型适配规则（与编译期共用 DYNAMIC_DIMENSION_RULES）。"""

    def _p(self, dimension, dynamic_key, relation=None):
        c = {
            'kind': 'relationship', 'dimension': dimension, 'operator': 'in',
            'valueSource': 'dynamic', 'dynamicKey': dynamic_key,
        }
        if relation:
            c['relation'] = relation
        return {'expr': '', 'groups': [{'expr': '', 'conditions': [c]}]}

    # ---- 正例 ----
    def test_dept_currentuser_departments_ok(self):
        self.assertIsNone(
            validate_scope_payload(self._p('dept', 'currentUser.departments', 'contains'), 'demand'))

    def test_owner_currentuser_id_ok(self):
        self.assertIsNone(validate_scope_payload(self._p('owner', 'currentUser.id'), 'demand'))

    def test_unit_managedunits_ok(self):
        self.assertIsNone(validate_scope_payload(self._p('unit', 'currentUser.managedUnits'), 'demand'))

    # ---- 维度不适配被拒 ----
    def test_owner_with_dept_source_rejected(self):
        reason = validate_scope_payload(self._p('owner', 'currentUser.departments'), 'demand')
        self.assertIsNotNone(reason)
        self.assertIn('不适用于维度', reason)

    def test_unit_with_user_source_rejected(self):
        reason = validate_scope_payload(self._p('unit', 'currentUser.id'), 'demand')
        self.assertIsNotNone(reason)
        self.assertIn('不适用于维度', reason)

    def test_dept_with_user_source_rejected(self):
        reason = validate_scope_payload(self._p('dept', 'currentUser.id'), 'demand')
        self.assertIsNotNone(reason)
        self.assertIn('不适用于维度', reason)

    # ---- 未注册来源 / 非法 relation ----
    def test_unregistered_source_rejected(self):
        reason = validate_scope_payload(self._p('dept', 'bogus.key'), 'demand')
        self.assertIsNotNone(reason)
        self.assertIn('未注册', reason)

    def test_dept_bad_relation_rejected(self):
        reason = validate_scope_payload(self._p('dept', 'currentUser.departments', 'bogus'), 'demand')
        self.assertIsNotNone(reason)
        self.assertIn('非法', reason)


class OptionsUnitShellTestCase(TestCase):
    """unit 维度空壳单元 emptyShell 标记（护栏一）。

    🔴 2026-10-15 兵哥拍板「去掉管理单元」后，options_payload **不再下发 unit 维度**
    （field_map.HIDDEN_DIMENSIONS 全局隐藏 unit，仅前端不可见，后端映射与
    iter_unit_scopes 展开逻辑一行未动，存量规则仍可执行）。
    故本用例拆成两条断言：
      ① options_payload 里 unit 维度**应缺席**（新行为，防回归）；
      ② emptyShell 空壳标记逻辑本身仍正确 —— 直接测 _unit_options()，
         护栏一（选中空壳单元看不到任何数据）不能因为隐藏维度而失去覆盖。
    """

    def test_unit_dimension_hidden_from_options(self):
        """去掉管理单元：options_payload 不应再下发 unit 维度。"""
        _mk_dept('BG')
        resp = options_payload()
        modules = {m['moduleKey']: m for m in resp['modules']}
        unit_dim = next(
            (d for d in modules['demand']['dimensions'] if d['key'] == 'unit'), None,
        )
        self.assertIsNone(
            unit_dim,
            '兵哥 2026-10-15 决策：管理单元维度应从 UI 下拉隐藏，'
            '后端仅不下发（HIDDEN_DIMENSIONS），不应出现在 dimensions 里',
        )

    def test_unit_options_carry_empty_shell_flag(self):
        """护栏一：emptyShell 标记仍正确（直接测取值函数，与是否下发解耦）。"""
        bg = _mk_dept('BG')
        u_ok = ManagementUnit.objects.create(
            unit_name='OK', org_scope=[{'deptId': str(bg.id)}], status=1,
        )
        u_shell = ManagementUnit.objects.create(
            unit_name='SHELL', org_scope=None, status=1,
        )
        unit_opts = _unit_options()
        by_id = {o['id']: o for o in unit_opts}
        self.assertIn(u_shell.id, by_id)
        self.assertTrue(by_id[u_shell.id].get('emptyShell'))
        self.assertIn(u_ok.id, by_id)
        self.assertNotIn('emptyShell', by_id[u_ok.id])
