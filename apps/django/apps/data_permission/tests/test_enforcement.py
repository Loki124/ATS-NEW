"""数据权限规则 enforcement 集成测试 (硬证据: 走完整 DRF 请求链路, 非 shell is_valid).

验证:
- 行级 ROW 规则 (按 部门 维度, DEPT) 真过滤候选人列表 (referrer__department ∈ 本部门).
- 列级 COLUMN 规则 (按 用户 维度) 真脱敏/隐藏字段 (NONE 移除, MASK 脱敏).
- 无规则时回退 scope_resolver (SELF), 证明差异化来自 DataPermissionRule.
- 规则停用(status=0) 即失效.
- 超管 bypass (与 FieldACL 既有语义一致).
"""
from django.core.cache import cache

from rest_framework.test import APITestCase, APIClient

from apps.core.models import User, Department
from apps.core.models_permission_v2 import RoleV2, RolePermissionV2, UserRoleV2
from apps.candidate.models import Candidate
from apps.data_permission.models import DataPermissionRule


def _user(username, dept=None, superuser=False):
    return User.objects.create_user(
        username, password='x',
        is_superuser=superuser, is_staff=superuser,
        department_id=dept,
    )


class DataPermissionEnforcementTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cache.clear()
        cls.d1 = Department.objects.create(id='D1', name='技术部', code='D1')
        cls.d2 = Department.objects.create(id='D2', name='产品部', code='D2')

        cls.creator = _user('creator', dept='D1')  # 候选人 created_by (非 u_hr)
        cls.u_hr = _user('u_hr', dept='D1')        # 被测 HR, 本部门
        cls.u_other = _user('u_other', dept='D2')  # 其他部门
        cls.r1 = _user('r1', dept='D1')            # 推荐人 (本部)
        cls.r2 = _user('r2', dept='D2')            # 推荐人 (他部)
        cls.su = _user('su', superuser=True)

        # 授权: HR 角色拥有 recruit:candidate:list
        RoleV2.objects.create(role_code='HR', system_code='recruit', status=1)
        RolePermissionV2.objects.create(
            role_code='HR', resource_code='recruit:candidate:list', system_code='recruit')
        UserRoleV2.objects.create(user_id=cls.u_hr.pk, role_code='HR', system_code='recruit')
        UserRoleV2.objects.create(user_id=cls.u_other.pk, role_code='HR', system_code='recruit')

        cls.c1 = Candidate.objects.create(
            name='张A', phone='13800000001', current_company='腾讯',
            referrer=cls.r1, created_by=cls.creator, current_state='APPLIED')
        cls.c2 = Candidate.objects.create(
            name='李B', phone='13800000002', current_company='阿里',
            referrer=cls.r2, created_by=cls.creator, current_state='APPLIED')
        # 列级测试专用: created_by=u_hr → u_hr 可经 SELF 行级检索到, 隔离列级验证
        cls.c3 = Candidate.objects.create(
            name='王C', phone='13800000003', current_company='字节',
            referrer=cls.r1, created_by=cls.u_hr, current_state='APPLIED')

    def setUp(self):
        cache.clear()

    # ---- 行级 ----
    def test_no_rule_falls_back_to_self(self):
        """无 DataPermissionRule → u_hr 走 scope_resolver SELF → 看不到他人创建的 c1/c2."""
        client = APIClient()
        client.force_authenticate(user=self.u_hr)
        resp = client.get('/api/v1/candidates/')
        self.assertEqual(resp.status_code, 200)
        ids = {c['id'] for c in resp.json()['data']}
        self.assertNotIn(self.c1.id, ids)
        self.assertNotIn(self.c2.id, ids)

    def test_row_dept_rule_filters_list(self):
        """DEPT 行级规则 (部门维度=D1) → u_hr 仅见本部推荐人 c1, 不见 c2."""
        DataPermissionRule.objects.create(
            dimension_type='DEPARTMENT', dimension_value='D1',
            level='ROW', scope_type='DEPT', status=1,
        )
        cache.clear()
        client = APIClient()
        client.force_authenticate(user=self.u_hr)
        resp = client.get('/api/v1/candidates/')
        self.assertEqual(resp.status_code, 200)
        ids = {c['id'] for c in resp.json()['data']}
        self.assertIn(self.c1.id, ids, '本部候选人应可见')
        self.assertNotIn(self.c2.id, ids, '他部候选人应被行级规则过滤')

    def test_row_rule_disabled_no_effect(self):
        """规则停用(status=0) → 回退 SELF, c1 不可见."""
        r = DataPermissionRule.objects.create(
            dimension_type='DEPARTMENT', dimension_value='D1',
            level='ROW', scope_type='DEPT', status=0,
        )
        cache.clear()
        client = APIClient()
        client.force_authenticate(user=self.u_hr)
        resp = client.get('/api/v1/candidates/')
        ids = {c['id'] for c in resp.json()['data']}
        self.assertNotIn(self.c1.id, ids)
        # 启用后再测一次, 证明是规则在驱动
        r.status = 1
        r.save()
        cache.clear()
        resp = client.get('/api/v1/candidates/')
        ids = {c['id'] for c in resp.json()['data']}
        self.assertIn(self.c1.id, ids)

    # ---- 列级 ----
    def test_column_none_hides_field(self):
        """USER 维度 NONE 规则命中 name → 详情接口不返回 name."""
        DataPermissionRule.objects.create(
            dimension_type='USER', dimension_value=str(self.u_hr.pk),
            level='COLUMN', entity='candidate', field='name',
            permission='NONE', status=1,
        )
        cache.clear()
        client = APIClient()
        client.force_authenticate(user=self.u_hr)
        resp = client.get(f'/api/v1/candidates/{self.c3.id}/')
        self.assertEqual(resp.status_code, 200)
        obj = resp.json().get('data', resp.json())
        self.assertNotIn('name', obj, 'NONE 规则应移除 name 字段')
        # 非敏感字段仍可见, 证明只是 name 被收口
        self.assertIn('id', obj)

    def test_column_mask_transforms_value(self):
        """USER 维度 MASK 规则命中 current_company → 值被脱敏 (≠ 原文)."""
        DataPermissionRule.objects.create(
            dimension_type='USER', dimension_value=str(self.u_hr.pk),
            level='COLUMN', entity='candidate', field='current_company',
            permission='MASK', status=1,
        )
        cache.clear()
        client = APIClient()
        client.force_authenticate(user=self.u_hr)
        resp = client.get(f'/api/v1/candidates/{self.c3.id}/')
        obj = resp.json().get('data', resp.json())
        # 响应经全局 camel-case 渲染, 输出 key 为 currentCompany
        self.assertIn('currentCompany', obj)
        self.assertNotEqual(obj['currentCompany'], '字节', 'MASK 规则应脱敏原值')

    # ---- 超管 bypass ----
    def test_superuser_bypass(self):
        """超管不经 DataPermissionRule 行级/列级限制."""
        DataPermissionRule.objects.create(
            dimension_type='DEPARTMENT', dimension_value='D1',
            level='ROW', scope_type='DEPT', status=1)
        DataPermissionRule.objects.create(
            dimension_type='USER', dimension_value=str(self.u_hr.pk),
            level='COLUMN', entity='candidate', field='name',
            permission='NONE', status=1)
        cache.clear()
        client = APIClient()
        client.force_authenticate(user=self.su)
        resp = client.get('/api/v1/candidates/')
        ids = {c['id'] for c in resp.json()['data']}
        self.assertIn(self.c1.id, ids)
        self.assertIn(self.c2.id, ids)
        detail = client.get(f'/api/v1/candidates/{self.c1.id}/')
        obj = detail.json().get('data', detail.json())
        self.assertEqual(obj.get('name'), '张A', '超管应看到明文 name')
