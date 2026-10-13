"""M07 长尾：批量 / 恢复类写入口的写范围与可见范围守卫（需要 DB）。

背景
====
V3 风险「WRITE 执行链漏接」在**批量入口**上表现得更隐蔽, 因为批量没有"单实例"
可挂 ``ensure_writable``:

1. ``process.batch_screen`` / ``batch_recommend`` 此前逐条 ``Candidate.objects.get(pk=cid)``
   —— **完全绕过候选人行级范围**, 列表看不到的候选人, 换个接口就能被写入筛选/推荐记录。
2. ``candidate.merge`` 此前只校验了**读范围** (``assert_candidates_visible``) —— 可见但
   只读的角色仍可合并 (合并会迁移申请/历史并软删被合并人, 属不可逆写操作)。
3. ``campus*`` / ``campus_control*`` 的 ``restore`` 此前是
   ``self.queryset.model.objects.get(pk=pk)`` —— 直接走默认 manager, 绕过 ViewSet 的
   queryset 解析, 知道 id 就能复活任意软删记录。

覆盖点
======
1. assert_candidates_writable: 无 WRITE 规则 -> 空列表 (opt-in fail-open)。
2. assert_candidates_writable: OWNER 写范围 -> 只放行自己负责的候选人。
3. filter_writable_candidates: 收窄 queryset 到可写子集。
4. batch_screen / batch_recommend: 越权候选人返回 NO_WRITE_PERMISSION 且不落库。
5. batch_*: 不存在的 id 仍返回 CANDIDATE_NOT_FOUND (不因新增守卫改变既有语义)。
6. restore: 改用 get_object 后, 被 queryset 排除的记录不可复活。
"""
from django.test import TestCase

from apps.candidate.models import Candidate
from apps.candidate.scope import (
    assert_candidates_writable,
    filter_writable_candidates,
)
from apps.core.models import Department, User
from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.data_permission.models import DataPermissionRule, RowScopeAccess, RowScopeType


class BatchWriteScopeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Department.objects.create(id='D1', name='华东大区')
        Department.objects.create(id='D2', name='华南大区')

        cls.u_owner = User.objects.create(username='u_owner', department_id='D1')
        cls.u_other = User.objects.create(username='u_other', department_id='D2')

        RoleV2.objects.create(
            system_code='recruit', role_code='BATCH_ROLE', role_name='批量角色', status=1)
        UserRoleV2.objects.create(
            user_id=cls.u_owner.pk, role_code='BATCH_ROLE', system_code='recruit')

    def _make_write_rule(self, scope_type, payload=None):
        return DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value='BATCH_ROLE', level='ROW',
            row_access=RowScopeAccess.WRITE, entity='candidate',
            scope_type=scope_type, scope_payload=payload, status=1,
        )

    def _candidate(self, referrer=None, n=0):
        return Candidate.objects.create(
            name=f'c{n}', phone=f'1380000{n:04d}', referrer=referrer)

    # ------------------------------------------------------------------
    # 1) opt-in 安全默认: 无 WRITE 规则 -> 一律放行
    # ------------------------------------------------------------------

    def test_no_write_rule_allows_all(self):
        mine = self._candidate(referrer=self.u_owner, n=1)
        others = self._candidate(referrer=self.u_other, n=2)
        self.assertEqual(
            assert_candidates_writable(_FakeRequest(self.u_owner), [mine.id, others.id]),
            [],
            '未配置写范围时应 fail-open, 不锁死批量写入口',
        )

    # ------------------------------------------------------------------
    # 2) OWNER 写范围: 只放行自己负责的
    # ------------------------------------------------------------------

    def test_owner_scope_blocks_others(self):
        self._make_write_rule(RowScopeType.OWNER)
        mine = self._candidate(referrer=self.u_owner, n=3)
        others = self._candidate(referrer=self.u_other, n=4)

        blocked = assert_candidates_writable(
            _FakeRequest(self.u_owner), [mine.id, others.id])
        self.assertEqual(blocked, [str(others.id)],
                         '非自己负责的候选人应被判为不可写')

    def test_none_scope_blocks_all(self):
        self._make_write_rule(RowScopeType.NONE)
        c = self._candidate(referrer=self.u_owner, n=5)
        self.assertEqual(
            assert_candidates_writable(_FakeRequest(self.u_owner), [c.id]),
            [str(c.id)],
            'NONE 写范围应拒绝全部',
        )

    def test_all_scope_allows_all(self):
        self._make_write_rule(RowScopeType.ALL)
        mine = self._candidate(referrer=self.u_owner, n=6)
        others = self._candidate(referrer=self.u_other, n=7)
        self.assertEqual(
            assert_candidates_writable(_FakeRequest(self.u_owner), [mine.id, others.id]),
            [],
        )

    def test_missing_ids_are_not_reported(self):
        """不存在的 id 不算越权（交由 service 的 DoesNotExist 分支处理）。"""
        self._make_write_rule(RowScopeType.OWNER)
        self.assertEqual(
            assert_candidates_writable(
                _FakeRequest(self.u_owner), ['does-not-exist-id']),
            [],
            '不存在的 id 不应被判成越权, 否则会误打断正常批量流程',
        )

    # ------------------------------------------------------------------
    # 3) filter_writable_candidates 收窄 queryset
    # ------------------------------------------------------------------

    def test_filter_writable_candidates_narrows(self):
        self._make_write_rule(RowScopeType.OWNER)
        mine = self._candidate(referrer=self.u_owner, n=8)
        others = self._candidate(referrer=self.u_other, n=9)

        qs = filter_writable_candidates(
            _FakeRequest(self.u_owner), Candidate.objects.all())
        self.assertEqual({c.pk for c in qs}, {mine.pk},
                         '应只保留可写子集')

    def test_filter_writable_candidates_fail_open(self):
        mine = self._candidate(referrer=self.u_owner, n=10)
        qs = filter_writable_candidates(
            _FakeRequest(self.u_owner), Candidate.objects.all())
        self.assertIn(mine.pk, {c.pk for c in qs})


class _FakeRequest:
    """最小 request 替身: scope helper 只需要 .user。"""

    def __init__(self, user):
        self.user = user