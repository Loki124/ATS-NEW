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


def _known_disabled_codes() -> set:
    """库内**有意停用**的资源码集合（跨迁移汇总）。

    停用码的语义是「功能已下线」：has_perm 对 status=0 的码一律拒绝
    （apps/core/permission_check.py:57-58），所以视图声明停用码是
    **有意关闭该端点**，不是「忘记注册」的缺口 —— 不应报为守卫失败。

    来源:
      - 0033.KNOWN_DISABLED_CODES = 0026.DISABLED_CODES + 0029.ORPHAN_CODES
        + 0029.ZOMBIE_BUTTON_CODES（28 条）
      - 0030.MOU_CODES（5 条）—— mou 整族停用，但未并入 0033 清单（0030 早于 0033）
      - 0050.USER_GROUPS_CODES（1 条）—— 用户组管理功能整体下线（2026-10-21）
    """
    import importlib.util
    import pathlib

    def _load(name, rel):
        p = pathlib.Path(__file__).resolve().parents[1] / rel
        spec = importlib.util.spec_from_file_location(name, p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    m30 = _load('m30_disabled_probe', 'apps/core/migrations/0030_split_campus_resource_codes.py')
    m33 = _load('m33_disabled_probe', 'apps/core/migrations/0033_mark_disabled_resources.py')
    m50 = _load('m50_disabled_probe', 'apps/core/migrations/0050_disable_user_groups_resource.py')
    return (
        set(m33.KNOWN_DISABLED_CODES)
        | set(m30.MOU_CODES)
        | set(m50.USER_GROUPS_CODES)
    )


def test_declared_permission_codes_all_registered():
    """视图书写里 permission_required / map 用到的码都必须在 RESOURCES 里。

    2026-10-21（卡 A3）扩展两处：
      ① 排除**有意停用**的码族（mou 等）—— 停用码由 has_perm 恒拒，是「有意关闭」
         而非「忘记注册」，不应报为缺口。
      ② **派生码**也必须已注册 —— 旧版只校验显式声明的码，于是
         「声明 :list + 派生 :edit 未注册」这类缺口能溜过去：
         _derive 走 fallback 把写操作回退到读码校验 = 持列表码即可写（权限提升）。
         现在单码声明的视图，其 create/update/destroy 派生码一并校验。
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
    disabled = _known_disabled_codes()

    from apps.core.permissions_v2 import ACTION_SUFFIX, CUSTOM_ACTION_SUFFIX

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
                if code in disabled:
                    continue  # 有意停用的码族 = 端点有意关闭
                if code not in registered:
                    missing.add(f'{cls.__module__}.{cls.__name__}: {code}')

            # ② 派生码校验：单码声明时, 实际会执行的写方法派生码必须已注册
            #    判定口径与 V2Permission.has_permission 严格对齐：
            #      ViewSet → view.action = 动作名（create/update/partial_update/destroy + 自定义 @action）
            #      APIView → view.action 恒为 None，map 按 HTTP method 小写匹配，
            #                未命中 map 的写方法一律派生 base + ':edit'（CUSTOM_ACTION_SUFFIX）
            if isinstance(declared, str) and declared and declared not in disabled:
                base = declared.rsplit(':', 1)[0] if ':' in declared else declared
                is_viewset = hasattr(cls, 'get_extra_actions')
                if is_viewset:
                    candidates = [
                        a for a in ('create', 'update', 'partial_update', 'destroy')
                        if hasattr(cls, a)
                    ]
                    for extra in cls.get_extra_actions():
                        if {m.upper() for m in extra.mapping} - {'GET', 'HEAD', 'OPTIONS'}:
                            candidates.append(extra.__name__)
                else:
                    candidates = [
                        m for m in ('post', 'put', 'patch', 'delete')
                        if hasattr(cls, m)
                    ]
                for act in candidates:
                    if act in mapping:
                        continue  # map 显式覆盖, 不派生
                    suffix = ACTION_SUFFIX.get(act if is_viewset else '', CUSTOM_ACTION_SUFFIX)
                    derived = f'{base}:{suffix}'
                    if derived == declared or derived in disabled:
                        continue
                    if derived not in registered:
                        missing.add(
                            f'{cls.__module__}.{cls.__name__}: {declared} → 派生 {derived} 未注册'
                        )

    walk(get_resolver().url_patterns)
    assert not missing, '视图声明了未注册的资源码（非超管将恒 403）:\n  ' + '\n  '.join(sorted(missing))
