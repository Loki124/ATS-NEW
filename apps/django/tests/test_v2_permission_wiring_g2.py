"""G2/G3 接线回归：此前对任意登录用户开放的端点，现在按资源码校验。

覆盖三件事：
1. **纯 APIView 的 method 键覆盖表**：POST-only 视图能用 `{'post': ':create'}`
   声明精确码（此前 action 恒 None，map 失效，只能退化成派生 :edit）。
2. **端点接线**：字典 / 码表 / 校招管控 / 候选人批量导出 —— 无对应码 → 403，
   持对应码 → 放行。
3. **seed 自洽**：模板里引用的码必须真实存在于 RESOURCES（否则回填/接线会落空）。

背景：本轮把裸 `IsAuthenticated` / `IsHROrAbove` 端点切到 V2Permission，
若无码即 403，为避免把现网用户锁死，同步补了
`backfill_role_permissions` 回填命令 + 模板配置码。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core import permissions_v2 as pv2
from apps.core.models_permission_v2 import RolePermissionV2
from apps.core.permissions_v2 import V2Permission
from tests.fixtures_common import _attach_role, _create_role_v2


def _client_for(user) -> APIClient:
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


def _scoped_user(department, username: str, codes: tuple[str, ...]):
    User = get_user_model()
    user = User.objects.create_user(
        username=username, password='Test@1234',
        employee_id=username.upper()[:20], department=department,
    )
    role = _create_role_v2(f'CUST_{username.upper()}'[:64], username)
    _attach_role(user, role)
    RolePermissionV2.objects.bulk_create([
        RolePermissionV2(role_code=role.role_code, resource_code=c, system_code='recruit')
        for c in codes
    ])
    return user


# ---------------------------------------------------------------- 1) method 键 map

class _StubView:
    permission_classes = [V2Permission]
    action = None
    permission_required = None
    permission_required_map = None

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


@pytest.fixture(autouse=True)
def _codes(monkeypatch):
    monkeypatch.setattr(pv2, 'known_resource_codes', lambda: {
        'recruit:candidate:list', 'recruit:candidate:create', 'recruit:candidate:edit',
    })


@pytest.fixture
def perm():
    return V2Permission()


@pytest.fixture
def user(db):
    return get_user_model().objects.create(username='u_g2_wiring', is_active=True)


@pytest.mark.django_db
class TestApiViewMethodKeyedMap:
    """纯 APIView (action=None) 下, permission_required_map 按 HTTP method 匹配。"""

    def test_post_uses_exact_code(self, rf, perm, user):
        request = rf.post('/x/', {}, format='json')
        request.user = user
        view = _StubView(
            permission_required='recruit:candidate:list',
            permission_required_map={'post': 'recruit:candidate:create'},
        )
        assert perm.has_permission(request, view) is False

    def test_get_falls_back_to_permission_required(self, rf, perm, user, monkeypatch):
        monkeypatch.setattr(
            'apps.core.permissions_v2.has_perm',
            lambda u, code: code == 'recruit:candidate:list',
        )
        request = rf.get('/x/')
        request.user = user
        view = _StubView(
            permission_required='recruit:candidate:list',
            permission_required_map={'post': 'recruit:candidate:create'},
        )
        assert perm.has_permission(request, view) is True

    def test_action_keyed_map_still_wins_for_viewset(self, rf, perm, user, monkeypatch):
        monkeypatch.setattr(
            'apps.core.permissions_v2.has_perm',
            lambda u, code: code == 'recruit:candidate:edit',
        )
        request = rf.post('/x/', {}, format='json')
        request.user = user
        view = _StubView(
            action='approve',
            permission_required='recruit:candidate:list',
            permission_required_map={'approve': 'recruit:candidate:edit', 'post': 'recruit:other:code'},
        )
        assert perm.has_permission(request, view) is True


# ---------------------------------------------------------------- 2) 端点接线

@pytest.mark.django_db
class TestEndpointsRequireCodes:
    def test_dictionary_types_denied_without_code(self, department):
        u = _scoped_user(department, 'g2_dict_denied', ('recruit:candidate:list',))
        resp = _client_for(u).get('/api/v1/dictionary-types/')
        assert resp.status_code == 403

    def test_dictionary_types_allowed_with_code(self, department):
        u = _scoped_user(department, 'g2_dict_ok', ('recruit:settings:dictionary:list',))
        resp = _client_for(u).get('/api/v1/dictionary-types/')
        assert resp.status_code == 200

    def test_code_tables_require_code(self, department):
        u = _scoped_user(department, 'g2_ct_denied', ('recruit:candidate:list',))
        resp = _client_for(u).get('/api/v1/code-tables/regions/')
        assert resp.status_code == 403

    def test_campus_control_requires_code(self, department):
        u = _scoped_user(department, 'g2_campus_denied', ('recruit:candidate:list',))
        resp = _client_for(u).get('/api/v1/campus/dimensions/')
        assert resp.status_code == 403


# ---------------------------------------------------------------- 3) seed 自洽

def test_template_codes_all_exist_in_resources():
    """模板引用的码必须都在 RESOURCES 里 —— 否则回填与接线都会落空。"""
    import importlib.util
    import pathlib
    seed_path = pathlib.Path(__file__).resolve().parents[1] / (
        'apps/core/management/commands/seed_v2_init.py'
    )
    spec = importlib.util.spec_from_file_location('seed_v2_init_probe', seed_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    resource_codes = {code for code, _name, _type, _module in mod.RESOURCES}
    for tpl in mod.TEMPLATES:
        missing = [c for c in tpl['codes'] if c not in resource_codes]
        assert not missing, f'{tpl["code"]} 引用了未定义资源码: {missing}'


def test_declared_permission_codes_all_registered():
    """视图书写里 permission_required / map 用到的码都必须在 RESOURCES 里。

    缺失时 _derive 会回退并打警告日志，等于该端点对非超管恒 403。
    """
    import importlib.util
    import pathlib
    from django.urls import get_resolver
    seed_path = pathlib.Path(__file__).resolve().parents[1] / (
        'apps/core/management/commands/seed_v2_init.py'
    )
    spec = importlib.util.spec_from_file_location('seed_v2_init_probe2', seed_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    registered = {code for code, _n, _t, _m in mod.RESOURCES}

    from apps.core.permissions_v2 import CUSTOM_ACTION_SUFFIX  # noqa: F401

    missing: set[str] = set()
    seen: set[int] = set()

    def walk(patterns):
        for p in patterns:
            if hasattr(p, 'url_patterns'):
                walk(p.url_patterns)
            cb = getattr(p, 'callback', None)
            cls = getattr(cb, 'cls', None) or getattr(cb, 'view_class', None)
            if cls is None or id(cls) in seen:
                continue
            seen.add(id(cls))
            declared = getattr(cls, 'permission_required', None)
            mapping = getattr(cls, 'permission_required_map', None) or {}
            values = []
            if isinstance(declared, str):
                values.append(declared)
            elif isinstance(declared, (list, tuple)):
                values += list(declared)
            for v in mapping.values():
                values += list(v) if isinstance(v, (list, tuple)) else [v]
            for code in values:
                if code not in registered:
                    missing.add(f'{cls.__module__}.{cls.__name__}: {code}')

    walk(get_resolver().url_patterns)
    assert not missing, '视图声明了未注册的资源码（非超管将恒 403）:\n  ' + '\n  '.join(sorted(missing))
