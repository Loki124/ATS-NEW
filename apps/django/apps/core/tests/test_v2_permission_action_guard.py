"""V2Permission 按 action 鉴权 + 写操作守卫的回归测试.

背景 (2026-10-08 审查):
    V2Permission 此前只校验视图级**静态**权限码, 不区分 HTTP 方法 / action,
    且视图未声明 permission_required 时对写操作也默认放行。后果:

    1. 只持 `recruit:user_role:list` 的账号可对 UserRoleViewSet 发 POST,
       写入 role_code='SUPER_ADMIN' → 完整权限提升。
    2. DepartmentViewSet 未声明任何权限码 → 任意登录用户可增删改部门。

本文件锁定修复后的行为, 防止回退。
"""
import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from apps.core import permissions_v2 as pv2
from apps.core.permissions_v2 import V2Permission

# ---------------------------------------------------------------- stubs

class _View:
    """最小视图桩: 只带 permission 相关属性 + action."""

    permission_classes = [V2Permission]
    action = None
    permission_required = None
    permission_required_map = None

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ---------------------------------------------------------------- fixtures

@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create(username='u_action_guard', is_active=True)


@pytest.fixture(autouse=True)
def _known_codes(monkeypatch):
    """固定已注册权限码集合, 不依赖 seed / DB。"""
    monkeypatch.setattr(
        pv2, 'known_resource_codes',
        lambda: {
            'recruit:candidate:list', 'recruit:candidate:create',
            'recruit:candidate:edit', 'recruit:candidate:delete',
            'recruit:user_role:list', 'recruit:user_role:create',
            'recruit:user_role:edit', 'recruit:user_role:delete',
            'recruit:invitation:list', 'recruit:invitation:create',
        },
    )


@pytest.fixture
def granted(monkeypatch):
    """把 has_perm 换成按 granted 集合判定, 并记录实际被校验的权限码。"""
    state = {'codes': set(), 'asked': []}

    def fake_has_perm(u, code):
        state['asked'].append(code)
        return code in state['codes']

    monkeypatch.setattr(pv2, 'has_perm', fake_has_perm)
    return state


def _check(method, view, user):
    req = APIRequestFactory().generic(method, '/x/')
    req.user = user
    return V2Permission().has_permission(req, view)


# ---------------------------------------------------------------- 权限提升回归

@pytest.mark.django_db
@pytest.mark.v2_permission
def test_create_requires_create_code_not_list(factory, user, granted):
    """核心回归: 只持 :list 的账号不得 create (原实现用 :list 放行了写操作)。"""
    granted['codes'] = {'recruit:user_role:list'}
    view = _View(action='create', permission_required='recruit:user_role:list')

    assert _check('post', view, user) is False
    assert granted['asked'] == ['recruit:user_role:create']


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_create_allowed_when_holding_create_code(user, granted):
    granted['codes'] = {'recruit:user_role:create'}
    view = _View(action='create', permission_required='recruit:user_role:list')

    assert _check('post', view, user) is True


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_list_still_requires_declared_code(user, granted):
    """读操作行为不变: 仍校验声明的原码。"""
    granted['codes'] = {'recruit:candidate:list'}
    view = _View(action='list', permission_required='recruit:candidate:list')

    assert _check('get', view, user) is True
    assert granted['asked'] == ['recruit:candidate:list']


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_update_maps_to_edit_and_destroy_to_delete(user, granted):
    granted['codes'] = {'recruit:candidate:edit', 'recruit:candidate:delete'}
    for action, method, expected in (
        ('update', 'put', 'recruit:candidate:edit'),
        ('partial_update', 'patch', 'recruit:candidate:edit'),
        ('destroy', 'delete', 'recruit:candidate:delete'),
    ):
        granted['asked'].clear()
        view = _View(action=action, permission_required='recruit:candidate:list')
        assert _check(method, view, user) is True
        assert granted['asked'] == [expected]


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_custom_action_maps_to_edit(user, granted):
    """自定义 @action (如 candidate.merge) 按 edit 校验。"""
    granted['codes'] = {'recruit:candidate:list'}
    view = _View(action='merge', permission_required='recruit:candidate:list')

    assert _check('post', view, user) is False
    assert granted['asked'] == ['recruit:candidate:edit']


# ---------------------------------------------------------------- 未声明守卫

@pytest.mark.django_db
@pytest.mark.v2_permission
def test_undeclared_write_is_denied(user, granted, settings):
    """未声明任何权限码的写操作 → 拒绝 (这是 DepartmentViewSet 的洞)。"""
    settings.V2_STRICT_WRITE_GUARD = True
    view = _View(action='create')

    assert _check('post', view, user) is False
    assert granted['asked'] == []          # 没走到 has_perm, 直接被守卫拦下


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_undeclared_read_still_allowed(user, granted):
    """读路径默认放行是有意设计 (KPI/导出靠 ScopeQueryset + FieldAcl 收口)。"""
    view = _View(action='list')

    assert _check('get', view, user) is True


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_undeclared_write_shadow_mode(user, granted, settings):
    """灰度期 V2_STRICT_WRITE_GUARD=False 只告警不拦截, 便于收集遗漏清单。"""
    settings.V2_STRICT_WRITE_GUARD = False
    view = _View(action='destroy')

    assert _check('delete', view, user) is True


# ---------------------------------------------------------------- 覆盖表 / 回退

@pytest.mark.django_db
@pytest.mark.v2_permission
def test_permission_required_map_takes_priority(user, granted):
    """显式 action 覆盖表优先级最高, 用于 sync_resources → role:assign 这类场景。"""
    granted['codes'] = {'recruit:invitation:create'}
    view = _View(
        action='send_invitation',
        permission_required='recruit:invitation:list',
        permission_required_map={'send_invitation': 'recruit:invitation:create'},
    )

    assert _check('post', view, user) is True
    assert granted['asked'] == ['recruit:invitation:create']


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_missing_derived_code_falls_back_to_declared(user, granted):
    """资源只定义了 :list 时 (种子滞后), 回退校验原码, 不把合法写操作锁死。"""
    granted['codes'] = {'recruit:invitation:list'}
    view = _View(action='update', permission_required='recruit:invitation:list')
    # _known_codes 里没有 recruit:invitation:edit

    assert _check('put', view, user) is True
    assert granted['asked'] == ['recruit:invitation:list']


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_list_form_required_is_not_derived(user, granted):
    """permission_required 为列表 = 调用方已明确意图, 原样校验, 不做派生。"""
    granted['codes'] = {'recruit:invitation:list'}
    view = _View(
        action='create',
        permission_required=['recruit:invitation:list', 'recruit:invitation:create'],
    )

    assert _check('post', view, user) is True
    assert granted['asked'] == ['recruit:invitation:list']


# ---------------------------------------------------------------- 基础分支

@pytest.mark.django_db
@pytest.mark.v2_permission
def test_anonymous_denied(factory, granted):
    view = _View(action='list', permission_required='recruit:candidate:list')
    req = factory.get('/x/')
    req.user = AnonymousUser()

    assert V2Permission().has_permission(req, view) is False


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_superuser_bypasses_declared_codes(db, granted):
    from django.contrib.auth import get_user_model
    su = get_user_model().objects.create(
        username='su_action_guard', is_active=True, is_superuser=True,
    )
    view = _View(action='create', permission_required='recruit:user_role:list')

    assert _check('post', view, su) is True
    assert granted['asked'] == []
