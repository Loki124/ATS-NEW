"""Phase 0 / Phase 1 修复回归测试 (2026-08-03 寇豆码)

对应 docs/ARCHITECTURE_REVIEW_2026-08-03.md 的 R2 / R3 / R5 / R6 / R8 / R15。
这些用例的目的是把"曾经出过的洞"钉死, 防止后续改动悄悄退回去。
"""
import pytest
from rest_framework.test import APIClient

from apps.candidate.models import Candidate
from apps.candidate.serializers import CandidateDetailSerializer, CandidateListSerializer
from apps.field_acl.services import FieldAclService


# ============================================================
# R15 — Candidate.__str__ 不得泄漏明文手机号
# ============================================================
@pytest.mark.django_db
class TestR15CandidateStrMasksPhone:
    def test_str_does_not_contain_plaintext_phone(self):
        c = Candidate(name='张三', phone='13812348000')
        rendered = str(c)
        assert '13812348000' not in rendered, f'__str__ 泄漏明文手机号: {rendered}'
        assert rendered.endswith('(***8000)'), rendered

    def test_str_handles_empty_phone(self):
        c = Candidate(name='李四', phone='')
        assert str(c) == '李四 ()'


# ============================================================
# R2 — FieldAclService 真正接到 Candidate 序列化器上
# ============================================================
@pytest.mark.django_db
class TestR2FieldAclWiredIntoSerializers:
    @staticmethod
    def _make_candidate() -> Candidate:
        return Candidate.objects.create(
            name='王五',
            phone='13812348000',
            email='wangwu@example.com',
            id_card_no='110101199001011234',
        )

    @staticmethod
    def _ctx(user):
        request = APIClient().request  # 占位, 下面用简易对象替代
        del request

        class _Req:
            def __init__(self, u):
                self.user = u

        return {'request': _Req(user)}

    def test_list_serializer_masks_phone_and_email_for_hr(self, hr_user):
        cand = self._make_candidate()
        data = CandidateListSerializer(cand, context=self._ctx(hr_user)).data
        assert data['phone'] == '138****8000', data['phone']
        assert data['email'] == 'w***@example.com', data['email']
        assert data['name'] == '王五'

    def test_detail_serializer_masks_id_card_for_hr(self, hr_user):
        cand = self._make_candidate()
        data = CandidateDetailSerializer(cand, context=self._ctx(hr_user)).data
        assert '110101199001011234' not in str(data['id_card_no'])
        assert data['id_card_no'].startswith('110')
        assert data['id_card_no'].endswith('1234')

    def test_superuser_sees_plaintext(self, super_user):
        cand = self._make_candidate()
        data = CandidateDetailSerializer(cand, context=self._ctx(super_user)).data
        assert data['phone'] == '13812348000'
        assert data['id_card_no'] == '110101199001011234'

    def test_no_request_context_fails_closed_when_acl_strict(self):
        """acl_strict=True 的 HTTP 序列化器即便没拿到 request context 也 fail-closed 脱敏,
        防止未来有 view 实例化序列化器忘传 context 又漏明文 (BUG-2)。
        内部导出/同步等确需明文输出的场景应显式设 acl_strict = False (见 mixins.py)。"""
        cand = self._make_candidate()
        data = CandidateDetailSerializer(cand).data
        assert data['phone'] == '138****8000', data['phone']
        assert data['name'] == '王五'

    def test_anonymous_user_is_masked(self):
        """R2: 匿名用户原来直接 return data, 等于不登录反而看全明文."""
        from django.contrib.auth.models import AnonymousUser

        payload = {'name': '王五', 'phone': '13812348000'}
        result = FieldAclService.apply_acl('candidate', payload, AnonymousUser())
        assert result['phone'] == '138****8000'

    def test_default_sensitive_fields_use_real_model_field_names(self):
        """R2: 键名必须是模型上真实存在的字段, 否则规则命中不到."""
        fields = FieldAclService.DEFAULT_SENSITIVE_FIELDS['candidate']
        model_fields = {f.name for f in Candidate._meta.get_fields()}
        assert 'id_card_no' in fields
        assert 'id_card_no' in model_fields
        # current_salary 在 Candidate 上根本不存在, 不应出现在默认清单里
        assert 'current_salary' not in fields
        assert 'current_salary' not in model_fields


# ============================================================
# R8 — scope_resolver 的 DEPT 分支必须返回真实部门集合
# ============================================================
@pytest.mark.django_db
class TestR8DeptScopeNotDropped:
    def test_own_dept_ids_returns_user_department(self, hr_user, department):
        from apps.core.scope_resolver import _own_dept_ids

        assert _own_dept_ids(hr_user) == [department.id]

    def test_own_dept_ids_excludes_ancestors(self, hr_user, department):
        """DEPT 只含本部门 —— 含祖先等于向上越权."""
        from apps.core.models import Department
        from apps.core.scope_resolver import _own_dept_ids

        parent = Department.objects.create(
            id='dept-parent-001', name='总部', code='HQ', path='/总部',
        )
        department.parent = parent
        department.path = '/总部/测试部门'
        department.save()

        result = _own_dept_ids(hr_user)
        assert result == [department.id]
        assert parent.id not in result

    def test_dept_and_sub_includes_children(self, hr_user, department):
        from apps.core.models import Department
        from apps.core.scope_resolver import _dept_and_sub_ids

        child = Department.objects.create(
            id='dept-child-001', name='子部门', code='SUB',
            parent=department, path=f'{department.path}/子部门',
        )
        result = set(_dept_and_sub_ids(hr_user))
        assert department.id in result
        assert child.id in result

    def test_no_department_returns_empty(self, db):
        from django.contrib.auth import get_user_model
        from apps.core.scope_resolver import _dept_and_sub_ids, _own_dept_ids

        u = get_user_model().objects.create_user(
            username='nodept', password='Test@1234', employee_id='E999',
        )
        assert _own_dept_ids(u) == []
        assert _dept_and_sub_ids(u) == []


# ============================================================
# R5 / R6 — 安全敏感 stub 不许假成功; /login 必须有限流
# ============================================================
@pytest.mark.django_db
class TestR5R6StubEndpointsRefuse:
    # config/urls.py:117 把 api_v1_patterns 挂在 'api/v1/' 下, 所以 stub 的真实路径
    # 是 /api/v1/auth/register。不带前缀会被 config/urls.py:145 的 SPA fallback
    # (re_path 排除了 api/ 开头) 吃掉, 返 200 text/html。
    API = '/api/v1'

    def test_register_creates_pending_user_not_fake_success(self):
        client = APIClient()
        resp = client.post(
            f'{self.API}/auth/register',
            {'email': 'qa_new_user@corp.com', 'password': 'Secret123'},
            format='json',
        )
        assert resp.status_code == 201, resp.content
        assert resp.data['success'] is True
        assert resp.get('X-Stub') != 'true'
        # 真建出 is_active=False 的待审用户, 而非假成功
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(email='qa_new_user@corp.com')
        assert user.is_active is False
        from apps.accounts.models import RegistrationApplication
        assert RegistrationApplication.objects.filter(
            email='qa_new_user@corp.com', status='PENDING').exists()

    def test_change_password_actually_changes_password(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        u = User.objects.create_user(username='qa_cp2', email='qa_cp2@corp.com', password='oldpass123')
        client = APIClient(); client.force_authenticate(user=u)
        resp = client.post(
            f'{self.API}/auth/change-password/',
            {'old_password': 'oldpass123', 'new_password': 'newpass123'},
            format='json',
        )
        assert resp.status_code == 200, resp.content
        assert resp.get('X-Stub') != 'true'
        u.refresh_from_db()
        assert u.check_password('newpass123'), '改密后新密码未生效 (假成功)'
        assert not u.check_password('oldpass123'), '旧密码仍可用 (假成功)'

    def test_login_alias_has_same_throttle_as_real_login(self):
        """R6: /login 别名以前没限流, 换个 URL 就能绕开撞库保护."""
        from apps.core.views_auth import LoginRateThrottle
        from apps.referral.urls_stubs import login_alias

        throttles = getattr(login_alias.cls, 'throttle_classes', [])
        assert LoginRateThrottle in throttles, throttles


# ============================================================
# R3 — settings 入口默认必须是 prod, 未知值必须报错
# ============================================================
class TestR3SettingsDefaultsToProd:
    def test_default_settings_module_is_prod(self):
        from config.settings import DEFAULT_SETTINGS_MODULE

        assert DEFAULT_SETTINGS_MODULE == 'config.settings.prod'

    def test_wsgi_and_asgi_default_to_prod(self):
        import pathlib

        base = pathlib.Path(__file__).resolve().parent.parent / 'config'
        for name in ('wsgi.py', 'asgi.py'):
            content = (base / name).read_text(encoding='utf-8')
            assert "'config.settings.prod'" in content, name
            assert "setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')" not in content
