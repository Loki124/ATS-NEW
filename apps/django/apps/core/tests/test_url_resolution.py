"""#22 路由守卫：关键路径 resolve 不被抢路由 + 非空前缀按长度降序。

审计 CODE_REVIEW_2026-10-08 §2.2 将 config/urls.py 手工顺序敏感列为架构风险 (A 类)。
#22 改造后路由由 config/urls._build_api_v1_patterns() 声明表构建，本测试作为回归护栏：
  - 解析已知易被「空前缀 include」抢走的路径，断言落到正确的 app/视图；
  - 静态断言 _NON_EMPTY 已按前缀长度降序（长前缀优先 match，新增路由与插入位置无关）。
无需数据库，纯 URL 解析。
"""
from django.urls import resolve

from config.urls import _NON_EMPTY


def _func_module(resolver_match) -> str:
    return getattr(resolver_match.func, '__module__', '') or ''


def _func_repr(resolver_match) -> str:
    return repr(resolver_match.func)


def test_search_resolves_to_search_app_not_stub():
    # 全局统一搜索须命中 apps.search, 而非 urls_stubs 的 search stub (原 line 23 须先于 line 32)
    m = resolve('/api/v1/search/')
    assert 'apps.search' in _func_module(m), (
        f'/api/v1/search/ 被抢路由, 落到 {_func_module(m)} 而非 apps.search'
    )


def test_v2_permissions_resolves_before_core_urls():
    # V2 权限 resources/templates 须命中 urls_permission_v2, 而非 core.urls 的 permissions router
    m = resolve('/api/v1/permissions/resources/')
    assert 'permission_v2' in _func_module(m) or 'permission_v2' in _func_repr(m), (
        f'/api/v1/permissions/resources/ 被 core.urls 抢走, 落到 {_func_module(m)}'
    )


def test_auth_login_resolves_to_core_urls_auth():
    m = resolve('/api/v1/auth/login/')
    # 须命中 apps.core.views_auth (真登录端点), 而非 urls_stubs 的 auth stub
    assert 'views_auth' in _func_module(m) or 'views_auth' in _func_repr(m), (
        f'/api/v1/auth/login/ 未命中 views_auth, 落到 {_func_module(m)}'
    )


def test_candidates_list_resolves_to_candidate_app():
    m = resolve('/api/v1/candidates/')
    assert 'apps.candidate' in _func_module(m), (
        f'/api/v1/candidates/ 未命中 candidate app, 落到 {_func_module(m)}'
    )


def test_background_check_static_prefix_not_shadowed():
    # 静态前缀 suppliers 须命中 BackgroundCheckOrderViewSet, 而非被更短前缀 orders/ 抢
    m = resolve('/api/v1/background-check/orders/suppliers/')
    assert 'BackgroundCheckOrder' in _func_repr(m), (
        f'/api/v1/background-check/orders/suppliers/ 未命中 BackgroundCheckOrderViewSet, 落到 {_func_repr(m)}'
    )


def test_background_check_detail_route_resolves_with_pk():
    m = resolve('/api/v1/background-check/orders/abc-123/')
    assert m.kwargs.get('pk') == 'abc-123', (
        f'/api/v1/background-check/orders/<pk>/ 未正确解析 pk, kwargs={m.kwargs}'
    )


def test_non_empty_prefixes_sorted_by_length_desc():
    # #22: 构建产物中, 非空前缀 include 须按长度降序 (长前缀优先 match, 新增路由与位置无关)
    from django.urls.resolvers import URLResolver

    from config.urls import _FRONT_ORDERED, api_v1_patterns

    built = [
        p.pattern._route
        for p in api_v1_patterns
        if isinstance(p, URLResolver) and p.pattern._route != ''
    ]
    # 构建顺序 = 刻意前置块(_FRONT_ORDERED) + 空前缀块 + 排序后的 _NON_EMPTY
    expected = [p for p, _ in _FRONT_ORDERED] + [
        p for p, _ in sorted(_NON_EMPTY, key=lambda x: len(x[0]), reverse=True)
    ]
    assert built == expected, f'非空前缀未按长度降序构建: {built}'
