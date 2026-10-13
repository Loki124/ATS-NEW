"""动态取值条件（valueSource='dynamic'）单测。

覆盖需求：「需求的所属部门 包含 当前用户的负责部门」。

组织夹具（祖先链：ROOT > 智能BG > {前端组, 后端组, 测试组}；ROOT > 商业化BG）：
    ROOT
    ├─ 智能BG
    │   ├─ 前端组   ← 张三的 department
    │   ├─ 后端组   ← 张三是 leader
    │   └─ 测试组   ← 李四的 department
    └─ 商业化BG

fail-closed 约定（安全默认，任一条不满足即「看不到任何数据」而非「全部可见」）：
    · 用户上下文缺失 / 未认证
    · 动态值来源未注册
    · 用户不负责任何部门
    · 非 dept 维度误用 dynamic
    · 包含关系未注册
"""
from django.test import TestCase

from apps.core.models import Department, User
from apps.data_permission.expr_compiler import (
    compile_scope_q,
    validate_scope_payload,
)
from apps.demand.models import Demand
from apps.process.models import RecruitmentProcess


def _mk_dept(name: str, parent: Department | None = None) -> Department:
    return Department.objects.create(name=name, parent=parent)


def _dynamic_payload(relation='contains', dimension='dept', dynamic_key='currentUser.departments'):
    return {
        'expr': '',
        'groups': [
            {
                'expr': '',
                'conditions': [
                    {
                        'kind': 'relationship',
                        'dimension': dimension,
                        'operator': 'in',       # 动态模式下不参与编译，占位保持合法
                        'valueSource': 'dynamic',
                        'dynamicKey': dynamic_key,
                        'relation': relation,
                    }
                ],
            }
        ],
    }


class DynamicScopeTestCase(TestCase):
    def setUp(self):
        self.root = _mk_dept('ROOT')
        self.bg = _mk_dept('智能BG', self.root)
        self.fe = _mk_dept('前端组', self.bg)
        self.be = _mk_dept('后端组', self.bg)
        self.qa = _mk_dept('测试组', self.bg)
        self.sales = _mk_dept('商业化BG', self.root)

        self.zhang = User.objects.create(username='zhang', department=self.fe)
        self.be.leader = self.zhang
        self.be.save()

        self.li = User.objects.create(username='li', department=self.qa)

        # Demand.process 是 NOT NULL，端到端用例需要一个最小流程
        self.process = RecruitmentProcess.objects.create(code='W001', name='社招通用流程')

    # ---------- contains：需求部门是负责部门的祖先 ----------
    def test_contains_matches_ancestors_of_responsible_depts(self):
        q = compile_scope_q(_dynamic_payload('contains'), 'demand', user=self.zhang)
        matched = set(q.children[0][1])
        # 前端组 + 后端组（自身命中）+ 智能BG + ROOT（祖先命中）
        self.assertTrue({self.fe.id, self.be.id, self.bg.id, self.root.id} <= matched,
                        f'应命中负责部门自身及其祖先，实际 {matched}')
        # 兄弟部门与无关 BG 必须排除 —— 本需求最易漏的负例
        self.assertNotIn(self.qa.id, matched, '兄弟部门（测试组）不应可见')
        self.assertNotIn(self.sales.id, matched, '无关 BG（商业化BG）不应可见')

    def test_contains_result_is_deterministic_and_sorted(self):
        a = compile_scope_q(_dynamic_payload('contains'), 'demand', user=self.zhang)
        b = compile_scope_q(_dynamic_payload('contains'), 'demand', user=self.zhang)
        self.assertEqual(str(a), str(b))
        self.assertEqual(list(a.children[0][1]), sorted(a.children[0][1]))

    # ---------- exact / in_subtree / overlap ----------
    def test_exact_only_matches_own_depts(self):
        q = compile_scope_q(_dynamic_payload('exact'), 'demand', user=self.zhang)
        matched = set(q.children[0][1])
        self.assertEqual(matched, {self.fe.id, self.be.id})

    def test_in_subtree_includes_descendants(self):
        # 李四负责测试组且测试组无子部门 -> 视为恒等
        q = compile_scope_q(_dynamic_payload('in_subtree'), 'demand', user=self.li)
        matched = set(q.children[0][1])
        self.assertIn(self.qa.id, matched)
        self.assertNotIn(self.bg.id, matched, 'in_subtree 不含祖先')

    def test_overlap_unions_all_relations(self):
        q = compile_scope_q(_dynamic_payload('overlap'), 'demand', user=self.zhang)
        matched = set(q.children[0][1])
        self.assertTrue({self.fe.id, self.be.id, self.bg.id, self.root.id} <= matched)

    # ---------- fail-closed 护栏 ----------
    def test_no_user_context_fails_closed(self):
        q = compile_scope_q(_dynamic_payload(), 'demand', user=None)
        self.assertEqual(list(q.children[0][1]), [], '缺少用户上下文必须空集')

    def test_user_without_responsible_dept_fails_closed(self):
        orphan = User.objects.create(username='orphan')
        q = compile_scope_q(_dynamic_payload(), 'demand', user=orphan)
        self.assertEqual(list(q.children[0][1]), [], '无负责部门必须空集')

    def test_unregistered_source_fails_closed(self):
        q = compile_scope_q(_dynamic_payload(dynamic_key='bogus.key'), 'demand', user=self.zhang)
        self.assertEqual(list(q.children[0][1]), [], '未注册来源必须空集')

    def test_unregistered_relation_fails_closed(self):
        q = compile_scope_q(_dynamic_payload(relation='bogus'), 'demand', user=self.zhang)
        self.assertEqual(list(q.children[0][1]), [], '未注册包含关系必须空集')

    def test_dimension_value_type_mismatch_fails_closed(self):
        # M03：维度须与动态值类型适配。dept 维度配 user 值类型来源
        # （currentUser.id）属于维度不适配 -> fail-closed（非空壳兜底）。
        q = compile_scope_q(
            _dynamic_payload(dimension='dept', dynamic_key='currentUser.id'), 'demand', user=self.zhang,
        )
        self.assertEqual(list(q.children[0][1]), [], '维度与值类型不适配必须空集')

    def test_owner_dimension_accepts_current_user_id(self):
        # M03 新行为：owner 维度 + currentUser.id 现合法，编译为 Q(hr_id__in=[user.pk])
        q = compile_scope_q(
            _dynamic_payload(dimension='owner', dynamic_key='currentUser.id'), 'demand', user=self.zhang,
        )
        s = str(q)
        self.assertIn('hr_id', s)
        self.assertIn(str(self.zhang.pk), s)

    # ---------- 保存期校验 ----------
    def test_validate_dynamic_condition_ok(self):
        self.assertIsNone(validate_scope_payload(_dynamic_payload(), 'demand'))

    def test_validate_dynamic_rejects_dimension_value_type_mismatch(self):
        # M03：dept 维度配 user 值类型来源（currentUser.id）属于维度不适配 -> 拒绝
        reason = validate_scope_payload(
            _dynamic_payload(dimension='dept', dynamic_key='currentUser.id'), 'demand',
        )
        self.assertIsNotNone(reason)
        self.assertIn('不适用于维度', reason)

    def test_validate_dynamic_rejects_unregistered_source(self):
        reason = validate_scope_payload(_dynamic_payload(dynamic_key='nope'), 'demand')
        self.assertIsNotNone(reason)
        self.assertIn('未注册', reason)

    def test_validate_dynamic_rejects_unregistered_relation(self):
        reason = validate_scope_payload(_dynamic_payload(relation='nope'), 'demand')
        self.assertIsNotNone(reason)
        self.assertIn('非法', reason)

    # ---------- 向后兼容：存量静态 payload 行为不变 ----------
    def test_static_payload_without_user_is_unchanged(self):
        payload = {
            'expr': '',
            'groups': [{'expr': '', 'conditions': [
                {'dimension': 'dept', 'operator': 'in',
                 'values': [{'id': self.bg.id, 'label': '智能BG'}]},
            ]}],
        }
        with_user = compile_scope_q(payload, 'demand', user=self.zhang)
        without_user = compile_scope_q(payload, 'demand')
        self.assertEqual(str(with_user), str(without_user))

    def test_static_payload_missing_value_source_still_valid(self):
        """存量数据没有 valueSource 字段（缺省 static），不应因新字段而失效。"""
        payload = {
            'expr': '',
            'groups': [{'expr': '', 'conditions': [
                {'dimension': 'dept', 'operator': 'in',
                 'values': [{'id': self.bg.id, 'label': '智能BG'}]},
            ]}],
        }
        self.assertIsNone(validate_scope_payload(payload, 'demand'))
        q = compile_scope_q(payload, 'demand', user=self.zhang)
        self.assertEqual(list(q.children[0][1]), [self.bg.id])

    # ---------- 端到端：真实需求数据过滤 ----------
    def _mk_demand(self, code: str, dept: Department) -> Demand:
        return Demand.objects.create(
            code=code,
            title=f'需求-{code}',
            department=dept,
            requested_by=self.zhang,
            hr=self.zhang,
            headcount=1,
            process=self.process,
        )

    def test_e2e_visible_set_matches_requirement(self):
        """张三（前端组 + leader 后端组）应恰好看到挂在自身/后端组/智能BG 的需求。

        对应方案 §4.2：张三负责 {前端组, 后端组} -> contains 取祖先 {前端组, 后端组, 智能BG, ROOT}
        -> REQ-BG / REQ-FE / REQ-BE 可见；REQ-QA（兄弟部门）与 REQ-SALES（无关 BG）不可见。
        """
        self._mk_demand('REQ-BG', self.bg)
        self._mk_demand('REQ-FE', self.fe)
        self._mk_demand('REQ-BE', self.be)
        self._mk_demand('REQ-QA', self.qa)
        self._mk_demand('REQ-SALES', self.sales)

        q = compile_scope_q(_dynamic_payload('contains'), 'demand', user=self.zhang)
        visible = set(Demand.objects.filter(q).values_list('code', flat=True))
        self.assertEqual(visible, {'REQ-BG', 'REQ-FE', 'REQ-BE'})
        # 负例断言：兄弟部门与无关 BG 必须被挡在外面
        self.assertNotIn('REQ-QA', visible)
        self.assertNotIn('REQ-SALES', visible)

    def test_e2e_sibling_department_excluded(self):
        """李四只负责测试组 -> 看不到张三所在的前端组/后端组的需求。"""
        self._mk_demand('REQ-FE', self.fe)
        self._mk_demand('REQ-QA', self.qa)

        q = compile_scope_q(_dynamic_payload('contains'), 'demand', user=self.li)
        visible = set(Demand.objects.filter(q).values_list('code', flat=True))
        self.assertEqual(visible, {'REQ-QA'})

    def test_e2e_no_responsible_dept_sees_nothing(self):
        """无负责部门 -> fail-closed：一条需求都看不到（而非看到全部）。"""
        self._mk_demand('REQ-BG', self.bg)
        orphan = User.objects.create(username='orphan2')
        q = compile_scope_q(_dynamic_payload('contains'), 'demand', user=orphan)
        self.assertEqual(Demand.objects.filter(q).count(), 0)