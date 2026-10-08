"""Tests for V2Permission + ScopeQuerysetMixin."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.core.permissions_v2 import ScopeQuerysetMixin, V2Permission

User = get_user_model()


# ---------- V2Permission tests ----------


class _PermTestView(APIView):
    """Stub view for V2Permission tests."""
    permission_classes = [V2Permission]


class _PermRequiredView(APIView):
    permission_classes = [V2Permission]
    permission_required = 'recruit:test:menu:view'


class _PermRequiredListView(APIView):
    permission_classes = [V2Permission]
    permission_required = ['recruit:test:menu:view', 'recruit:test:button:create']


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.fixture
def user(db):
    return User.objects.create(username='u_v2perm', is_active=True)


@pytest.fixture
def admin_user(db):
    """Plain active user; test sets is_superuser=True explicitly."""
    return User.objects.create(username='admin_v2perm', is_active=True)


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_v2perm_anonymous_denied(factory):
    """未登录 → False (不查 DB)."""
    from django.contrib.auth.models import AnonymousUser
    view = _PermTestView()
    req = factory.get('/')
    req.user = AnonymousUser()
    perm = V2Permission()
    assert perm.has_permission(req, view) is False


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_v2perm_superuser_bypass(factory, admin_user):
    """superuser → True, 即便 view 声明了 permission_required 也不查 DB."""
    admin_user.is_superuser = True
    admin_user.save()
    view = _PermRequiredView()
    req = factory.get('/')
    req.user = admin_user
    perm = V2Permission()
    assert perm.has_permission(req, view) is True


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_v2perm_no_required_allows(factory, user):
    """view 不声明 permission_required → 放行 (依赖 ScopeQuerysetMixin)."""
    view = _PermTestView()
    req = factory.get('/')
    req.user = user
    perm = V2Permission()
    assert perm.has_permission(req, view) is True


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_v2perm_authenticated_no_match_returns_false(factory, user):
    """authenticated + 有 permission_required + 无 V2 角色 → False."""
    view = _PermRequiredView()
    req = factory.get('/')
    req.user = user
    perm = V2Permission()
    # user 无 V2 role_codes → has_perm 返回 False → V2Permission 拒绝
    assert perm.has_permission(req, view) is False


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_v2perm_list_required_any_match(factory, user):
    """permission_required = list 时, 任意一个匹配 → 走 has_perm (无 role → 全 False)."""
    view = _PermRequiredListView()
    req = factory.get('/')
    req.user = user
    perm = V2Permission()
    assert perm.has_permission(req, view) is False


# ---------- ScopeQuerysetMixin tests ----------


class _ScopedTestView(ScopeQuerysetMixin):
    """Stub view for ScopeQuerysetMixin tests. scope_field 默认 'created_by'."""
    scope_field = 'created_by'

    def __init__(self, user):
        self.request = type('Req', (), {'user': user})()


@pytest.fixture
def two_channels(db, user):
    """创建 2 个 Channel, user 是其中 1 个的 created_by."""
    from apps.channel.models import Channel
    owned = Channel.objects.create(name='owned', code='c_owned', category='OTHER', created_by=user)
    other = Channel.objects.create(name='other', code='c_other', category='OTHER')
    return owned, other


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_scope_queryset_superuser_no_filter(two_channels, admin_user):
    """superuser → 不加 WHERE 条件."""
    admin_user.is_superuser = True
    admin_user.save()
    view = _ScopedTestView(admin_user)
    from apps.channel.models import Channel
    scoped = view.scope_queryset(Channel.objects.all())
    assert scoped.count() == 2  # 两个都在


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_scope_queryset_no_units_returns_self_only(two_channels, user):
    """user 无 management_unit_ids + 无 tenant ALL → created_by=user SELF 兜底."""
    view = _ScopedTestView(user)
    from apps.channel.models import Channel
    scoped = view.scope_queryset(Channel.objects.all())
    assert scoped.count() == 1
    assert scoped.first().code == 'c_owned'


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_scope_queryset_all_scope_unfiltered(two_channels, user):
    """scope.all=True (L3 tenant) → 不过滤 (返回全部)."""
    from apps.core.models_permission_v2 import TenantConfig
    TenantConfig.objects.create(
        system_code='recruit',
        config_key='GLOBAL_DEFAULT_DATA_SCOPE',
        config_value='ALL',
    )
    view = _ScopedTestView(user)
    from apps.channel.models import Channel
    scoped = view.scope_queryset(Channel.objects.all())
    assert scoped.count() == 2  # 全部可见


