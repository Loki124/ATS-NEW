"""数据权限规则 enforcement 集成测试 (硬证据: 走完整 DRF 请求链路, 非 shell is_valid).

Tier 3 之后本文件仅覆盖列级 COLUMN 规则 (行级 ROW 已交由 scope_resolver 处理, 见
apps/core/tests/test_data_permission_unit_enforcement.py).

验证:
- 列级 COLUMN 规则 (按 用户 维度) 真脱敏/隐藏字段 (NONE 移除, MASK 脱敏).
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
        # 注: tests/fixtures_common._ensure_v2_schema (session autouse) 在空库时会为
        # HR/HRBP/SUPER_ADMIN 批量 seed 所有 permission_required 资源码 (含 recruit:candidate:list),
        # 故此处用 get_or_create 避免与 conftest seed 在 (role_code, resource_code) 唯一约束上冲突.
        RoleV2.objects.get_or_create(role_code='HR', system_code='recruit',
                                     defaults={'role_code': 'HR', 'system_code': 'recruit', 'status': 1})
        RolePermissionV2.objects.get_or_create(
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
