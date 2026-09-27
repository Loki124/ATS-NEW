"""QA 独立验证测试 (2026-08-03 严过关)

目的: 不采信 tests/test_phase1_security_fixes.py 的自证结果, 从**真实 HTTP 边界**
重新验证 Phase 1 的安全修复。

与工程师那份回归测试的差异:
  - R2: 工程师只在 serializer 层构造假 context 断言, 没有经过 ViewSet /
        get_serializer_class / CamelCase 渲染器。本文件直接打 /api/v1/candidates/,
        断言**渲染后的响应体里不含明文 PII**。
  - R5/R6: 补断言"501 之外, 数据库确实没被写" —— 假成功的核心危害是"说改了但没改",
        只查状态码不足以证明。
  - R8: 工程师只测了 _own_dept_ids / _dept_and_sub_ids 两个私有 helper,
        没有测 resolve_scope 的返回契约, 也没测下游 ScopeQuerysetMixin 是否真的
        按 department_ids 过滤。本文件补上这两层。
"""
import json

import pytest
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.core.models_permission_v2 import RoleV2
from tests.fixtures_common import _raw_attach_v2_role

PLAIN_PHONE = '13812348000'
PLAIN_EMAIL = 'wangwu@example.com'
PLAIN_ID_CARD = '110101199001011234'


def _make_candidate(**kw) -> Candidate:
    defaults = dict(
        name='王五',
        phone=PLAIN_PHONE,
        email=PLAIN_EMAIL,
        id_card_no=PLAIN_ID_CARD,
    )
    defaults.update(kw)
    return Candidate.objects.create(**defaults)


def _create_role_v2_with_scope(code: str, name: str, scope_type: str) -> RoleV2:
    """建一个指定 default_data_scope_type 的 V2 角色 (fixtures_common 的版本写死 ALL).

    2026-08-03 T01.1 (寇豆码): 适配 V2 fresh schema — 没有 V1 列 (code/name/is_builtin/is_active).
    T01.1 前: 写 V1+V2 hybrid (id=VARCHAR(32) PK + V1 列 + V2 列).
    T01.1 后: 写 V2 only (id=BigAuto + system_code/role_code/...).

    检测: 看 `code` 列是否存在. V1 hybrid 有, V2 fresh 无.
    """
    import uuid

    from django.utils import timezone

    with connection.cursor() as c:
        c.execute('PRAGMA table_info(roles)')
        cols = {row[1] for row in c.fetchall()}
        if 'code' in cols:
            # V1 hybrid (历史) — 写 V1 + V2 列
            c.execute(
                """INSERT INTO roles
                   (id, code, name, description, is_builtin, is_active, role_code, role_name,
                    system_code, status, default_data_scope_type, created_at, updated_at)
                   VALUES (%s, %s, %s, '', 0, 1, %s, %s, 'recruit', 1, %s, %s, %s)""",
                [
                    f'role-{code.lower()}-{uuid.uuid4().hex[:8]}', code, name, code, name,
                    scope_type, timezone.now(), timezone.now(),
                ],
            )
        else:
            # V2 fresh schema (T01.1 后) — 只写 V2 列
            c.execute(
                """INSERT INTO roles
                   (system_code, role_code, role_name, description,
                    is_system, status, default_data_scope_type, created_at, updated_at)
                   VALUES ('recruit', %s, %s, '', 0, 1, %s, %s, %s)""",
                [code, name, scope_type, timezone.now(), timezone.now()],
            )
    return RoleV2.objects.get(role_code=code, system_code='recruit')


# ============================================================
# R2 — 真实 HTTP 边界上的 PII 脱敏
# ============================================================
@pytest.mark.django_db
class TestR2MaskingAtHttpBoundary:
    """非特权角色打真实 API, 响应体不得出现明文 PII."""

    def test_list_endpoint_body_has_no_plaintext_pii(self, auth_hr_client):
        _make_candidate()
        resp = auth_hr_client.get('/api/v1/candidates/')
        assert resp.status_code == 200, resp.content[:300]
        body = resp.content.decode('utf-8')
        assert PLAIN_PHONE not in body, f'列表接口泄漏明文手机号: {body[:500]}'
        assert PLAIN_EMAIL not in body, f'列表接口泄漏明文邮箱: {body[:500]}'
        assert '138****8000' in body, f'未按预期脱敏: {body[:500]}'

    def test_detail_endpoint_body_has_no_plaintext_pii(self, auth_hr_client):
        cand = _make_candidate()
        resp = auth_hr_client.get(f'/api/v1/candidates/{cand.id}/')
        assert resp.status_code == 200, resp.content[:300]
        body = resp.content.decode('utf-8')
        assert PLAIN_PHONE not in body, f'详情接口泄漏明文手机号: {body[:800]}'
        assert PLAIN_EMAIL not in body, f'详情接口泄漏明文邮箱: {body[:800]}'
        assert PLAIN_ID_CARD not in body, f'详情接口泄漏明文身份证: {body[:800]}'

    def test_superuser_still_sees_plaintext(self, auth_client):
        """反向用例: 脱敏不能一刀切, 超管必须仍能看到明文, 否则是功能回归."""
        cand = _make_candidate()
        resp = auth_client.get(f'/api/v1/candidates/{cand.id}/')
        assert resp.status_code == 200, resp.content[:300]
        body = resp.content.decode('utf-8')
        assert PLAIN_PHONE in body, '超管被过度脱敏, 属于功能回归'

    def test_keyword_search_by_phone_does_not_echo_plaintext(self, auth_hr_client):
        """侧信道: 按手机号搜索命中后, 响应里同样不能回显明文."""
        _make_candidate()
        resp = auth_hr_client.get('/api/v1/candidates/', {'keyword': PLAIN_PHONE})
        assert resp.status_code == 200
        assert PLAIN_PHONE not in resp.content.decode('utf-8')


# ============================================================
# R5 / R6 — 注册/改密 已实现 → 验证真实行为 (真建待审用户 / 真改密), 而非 stub 501
# ============================================================
@pytest.mark.django_db
class TestR5R6RealEndpointsNotFakeSuccess:
    def test_register_creates_pending_user_not_fake_success(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        before = User.objects.count()
        resp = APIClient().post(
            '/api/v1/auth/register/',
            {'email': 'qa_probe_user@corp.com', 'password': 'Probe@12345'},
            format='json',
        )
        assert resp.status_code == 201, resp.content
        assert resp['Content-Type'].startswith('application/json'), resp['Content-Type']
        assert resp.data['success'] is True
        assert resp.get('X-Stub') != 'true', '不应再有 stub 头'
        # 真建出 is_active=False 的待审用户, 而非假成功
        user = User.objects.get(email='qa_probe_user@corp.com')
        assert user.is_active is False
        from apps.accounts.models import RegistrationApplication
        assert RegistrationApplication.objects.filter(
            email='qa_probe_user@corp.com', status='PENDING').exists()
        assert User.objects.count() == before + 1

    def test_change_password_actually_changes_password(self, hr_user):
        """核心验证: 旧密码必须失效、新密码必须生效 —— 接口真写库了."""
        from django.contrib.auth import authenticate

        client = APIClient()
        refresh = RefreshToken.for_user(hr_user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        resp = client.post(
            '/api/v1/auth/change-password/',
            {'old_password': 'Test@1234', 'new_password': 'BrandNew@9999'},
            format='json',
        )
        assert resp.status_code == 200, resp.content
        assert resp.get('X-Stub') != 'true'
        assert resp.data['success'] is True

        hr_user.refresh_from_db()
        assert authenticate(username='hr_zhang', password='Test@1234') is None, \
            '旧密码仍有效? 改密未生效'
        assert authenticate(username='hr_zhang', password='BrandNew@9999') is not None, \
            '新密码未生效, 说明改密没写库'

    def test_register_response_is_json_not_spa_html(self):
        """确认路径没被 SPA fallback 吃掉 (吃掉会返 200 text/html, 等于假成功)."""
        resp = APIClient().post(
            '/api/v1/auth/register/',
            {'email': 'qa_spa@corp.com', 'password': 'Probe@12345'},
            format='json',
        )
        assert resp['Content-Type'].startswith('application/json'), resp['Content-Type']
        assert resp.status_code == 201


# ============================================================
# R8 — resolve_scope 的返回契约 + 下游过滤是否真的用上了
# ============================================================
@pytest.mark.django_db
class TestR8DeptScopeContractAndDownstream:
    def test_resolve_scope_returns_department_ids_for_dept_role(self, db, department):
        from django.contrib.auth import get_user_model

        from apps.core.scope_resolver import resolve_scope

        role = _create_role_v2_with_scope('QA_DEPT_ROLE', '部门范围角色', 'DEPT')
        user = get_user_model().objects.create_user(
            username='qa_dept_user', password='Test@1234',
            employee_id='EQA1', department=department,
        )
        _raw_attach_v2_role(user, role)

        scope = resolve_scope(user)
        assert 'department_ids' in scope, f'DEPT 范围仍未返回 department_ids: {scope}'
        assert scope['department_ids'] == [department.id], scope
        assert scope != {'management_unit_ids': []}, 'DEPT 被静默降级成 SELF (R8 回归)'

    def test_resolve_scope_dept_and_sub_includes_children(self, db, department):
        from django.contrib.auth import get_user_model

        from apps.core.scope_resolver import resolve_scope

        child = Department.objects.create(
            id='dept-qa-child', name='QA子部门', code='QA_SUB',
            parent=department, path=f'{department.path}/QA子部门',
        )
        role = _create_role_v2_with_scope('QA_DEPTSUB_ROLE', '含子部门', 'DEPT_AND_SUB')
        user = get_user_model().objects.create_user(
            username='qa_deptsub_user', password='Test@1234',
            employee_id='EQA2', department=department,
        )
        _raw_attach_v2_role(user, role)

        scope = resolve_scope(user)
        assert set(scope.get('department_ids', [])) == {department.id, child.id}, scope

    def test_scope_queryset_actually_filters_by_department(self, db, department):
        """下游消费: ScopeQuerysetMixin 必须按 department_ids 过滤, 而不是退回 SELF."""
        from django.contrib.auth import get_user_model

        from apps.core.permissions_v2 import ScopeQuerysetMixin

        User = get_user_model()
        role = _create_role_v2_with_scope('QA_DEPT_QS_ROLE', '部门范围角色2', 'DEPT')
        user = User.objects.create_user(
            username='qa_qs_user', password='Test@1234',
            employee_id='EQA3', department=department,
        )
        _raw_attach_v2_role(user, role)

        other_dept = Department.objects.create(
            id='dept-qa-other', name='别的部门', code='QA_OTHER', path='/别的部门',
        )
        referrer_in = User.objects.create_user(
            username='ref_in', password='Test@1234',
            employee_id='EQA4', department=department,
        )
        referrer_out = User.objects.create_user(
            username='ref_out', password='Test@1234',
            employee_id='EQA5', department=other_dept,
        )
        c_in = _make_candidate(name='本部门候选人', phone='13800000001', referrer=referrer_in)
        c_out = _make_candidate(name='他部门候选人', phone='13800000002', referrer=referrer_out)

        class _View(ScopeQuerysetMixin):
            scope_field = 'referrer__department'

            def __init__(self, u):
                class _R:
                    pass
                self.request = _R()
                self.request.user = u

        qs = _View(user).scope_queryset(Candidate.objects.all())
        ids = set(qs.values_list('id', flat=True))
        assert c_in.id in ids, 'DEPT 范围下看不到本部门数据 (R8 未真正生效)'
        assert c_out.id not in ids, '跨部门数据泄漏 (IDOR)'


# ============================================================
# R3 — 生产配置强校验必须真的抛异常 (子进程实跑, 不做静态断言)
# ============================================================
class TestR3ProdValidationActuallyRaises:
    @pytest.mark.parametrize(
        'env_overrides,expect_fragment',
        [
            ({'DJANGO_SECRET_KEY': 'weak'}, 'DJANGO_SECRET_KEY'),
            ({'DJANGO_DEBUG': 'True'}, 'DEBUG 必须为 False'),
            ({'DJANGO_ALLOWED_HOSTS': '*'}, "ALLOWED_HOSTS 不能包含 '*'"),
            ({'CORS_ALLOWED_ORIGINS': ''}, 'CORS_ALLOWED_ORIGINS 不能为空'),
        ],
    )
    def test_prod_settings_reject_insecure_config(self, env_overrides, expect_fragment):
        import os
        import secrets
        import subprocess
        import sys

        env = dict(os.environ)
        env.update({
            'DJANGO_SETTINGS_MODULE': 'config.settings.prod',
            'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
            'DJANGO_DEBUG': 'False',
            'DJANGO_ALLOWED_HOSTS': 'ats.example.com',
            'CORS_ALLOWED_ORIGINS': 'https://ats.example.com',
        })
        env.update(env_overrides)
        proc = subprocess.run(
            [sys.executable, '-c', 'import django; django.setup()'],
            cwd=str(__import__('pathlib').Path(__file__).resolve().parent.parent),
            env=env, capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode != 0, f'不安全配置竟然启动成功了: {env_overrides}'
        assert 'ImproperlyConfigured' in proc.stderr, proc.stderr[-800:]
        assert expect_fragment in proc.stderr, proc.stderr[-800:]

    def test_unknown_settings_module_is_rejected_not_silently_dev(self):
        import os
        import subprocess
        import sys

        env = dict(os.environ)
        env['DJANGO_SETTINGS_MODULE'] = 'config.settings.staging'
        proc = subprocess.run(
            [sys.executable, '-c', 'import django; django.setup()'],
            cwd=str(__import__('pathlib').Path(__file__).resolve().parent.parent),
            env=env, capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode != 0
        assert 'ImproperlyConfigured' in proc.stderr
        assert '不是合法的配置模块' in proc.stderr


# ============================================================
# R15 — 日志/repr 层面不得落盘明文
# ============================================================
@pytest.mark.django_db
class TestR15NoPlaintextInStrOrRepr:
    def test_str_and_repr_are_masked(self):
        cand = _make_candidate()
        assert PLAIN_PHONE not in str(cand)
        assert PLAIN_PHONE not in repr(cand)

    def test_masking_helpers_are_stable(self):
        from apps.common.masking import mask_email, mask_id_card, mask_phone

        assert mask_phone(PLAIN_PHONE) == '138****8000'
        assert mask_email(PLAIN_EMAIL) == 'w***@example.com'
        assert mask_id_card(PLAIN_ID_CARD) == '110***********1234'
        # 边界: 空值不得抛异常
        for fn in (mask_phone, mask_email, mask_id_card):
            assert fn('') == ''
            assert fn(None) in ('', None)


# ============================================================
# R9 — 依赖清单与实际 venv 是否一致 (防「锁了但没装」)
# ============================================================
class TestR9RequirementsConsistency:
    def test_no_removed_packages_left_in_requirements(self):
        import pathlib
        import re

        req = (pathlib.Path(__file__).resolve().parent.parent / 'requirements.txt')
        content = req.read_text(encoding='utf-8')
        lines = [
            line.strip() for line in content.splitlines()
            if line.strip() and not line.strip().startswith('#')
        ]
        names = {re.split(r'[=<>!\[ ]', line, 1)[0].lower() for line in lines}
        # 2026-09-27 P0-4: django-fsm 3.x 已停止维护, 迁移到 django-fsm-2 (4.2.4)。
        #   两者提供同一个顶层模块 django_fsm, **只能留一个** —— 这正是 R9 当初把
        #   django-fsm-2 列进 banned 的原因 (当时是"两个并存"导致覆盖不确定)。
        #   现在方向反转: 保留维护中的 django-fsm-2, 禁掉停维护的 django-fsm 本体。
        #   实测 django-fsm-2 是超集: FSMModelMixin / FSMFieldMixin / _django_fsm
        #   元数据 / FSMField max_length=50 / ANY_STATE='*' 全部保留, 零代码改动。
        for banned in ('python-decouple', 'uvicorn', 'django-fsm'):
            assert banned not in names, f'requirements.txt 仍残留已废弃依赖: {banned}'
        assert any(
            line.startswith('django-fsm-2==') for line in lines
        ), '状态机依赖应为 django-fsm-2 (django-fsm 3.x 已停止维护)'
        assert any(line.startswith('cryptography==') for line in lines), \
            'cryptography 未显式锁版本'

    def test_pinned_versions_match_installed(self):
        """锁了版本但装的是别的 = 假锁. 抽查关键安全相关包."""
        import pathlib
        import re
        from importlib.metadata import PackageNotFoundError, version

        req = (pathlib.Path(__file__).resolve().parent.parent / 'requirements.txt')
        mismatches = []
        for line in req.read_text(encoding='utf-8').splitlines():
            line = line.split('#')[0].strip()
            m = re.match(r'^([A-Za-z0-9_.\-]+)==([0-9][^\s;]*)$', line)
            if not m:
                continue
            pkg, pinned = m.group(1), m.group(2)
            try:
                installed = version(pkg)
            except PackageNotFoundError:
                mismatches.append(f'{pkg}: 锁了 {pinned} 但未安装')
                continue
            if installed != pinned:
                mismatches.append(f'{pkg}: requirements={pinned} installed={installed}')
        assert not mismatches, '\n'.join(mismatches)
