"""URL 路由总入口"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse, Http404
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from apps.application.views import ApplicationViewSet
from apps.common.views import MediaDownloadView, MediaUploadView
from apps.demand.views import DemandConfigView
# 2026-08-28 寇豆码: 背调供应商异步回调入向端点（§5.2 验签，供应商签名保护，不鉴权）
from apps.integration.views import BackgroundCheckCallbackView, BackgroundCheckOrderViewSet

# === #22 路由注册式改造 (2026-10-09) ===
# 把 api_v1 下的路由拆成「显式有序块」+「按前缀长度降序块」, 消灭手工顺序敏感:
#   - 空前缀 include (挂在 api_v1 根) 彼此有真实优先级依赖 (V2 权限须先于 core.urls、
#     search 须先于 urls_stubs 的 search stub...), 无法由长度推导, 保持 EXACT 顺序。
#   - 非空前缀 include 彼此独立, 按 prefix 长度降序即可保证「长前缀优先 match」,
#     新增路由无需关心插入位置。
#   - 直接挂载的 APIView (background-check/*、media/*、system/config/demand) 同样
#     按长度降序, 其静态前缀不与任何 include 重叠。
# 守卫测试见 apps/django/apps/core/tests/test_url_resolution.py (resolve 关键路径断言无抢路由)。

# 1) 显式有序块: 非空前缀中 MUST 位于某空前缀 include 之前的 (search 须先于 urls_stubs)
_FRONT_ORDERED = [
    ('search/', 'apps.search.urls'),
    ('auth/', 'apps.core.urls_auth'),
]

# 2) 空前缀块 (顺序敏感, 禁止重排)
_EMPTY_PREFIX = [
    ('', 'apps.process.urls_round'),
    ('', 'apps.referral.alias_endpoints'),
    ('', 'apps.core.urls_permission_v2'),
    ('', 'apps.core.urls'),
    ('', 'apps.dictionary.urls'),
]

# 3) 其余非空前缀 (按长度降序, 顺序无关)
_NON_EMPTY = [
    ('stages/', 'apps.process.urls_stage'),
    ('recruitment-stages/', 'apps.process.urls_stage'),
    ('processes/', 'apps.process.urls_process'),
    ('process-stage-links/', 'apps.process.urls_link'),
    ('stage-rules/', 'apps.process.urls_rule'),
    ('entry-condition-rules/', 'apps.entry_condition.urls'),
    ('time-limit-rules/', 'apps.time_limit.urls'),
    ('automation-rules/', 'apps.automation.urls'),
    ('expressions/', 'apps.process.urls_expression'),
    ('candidates/', 'apps.candidate.urls'),
    ('candidates/add-candidate/', 'apps.add_candidate.urls'),
    ('applications/', 'apps.application.urls'),
    ('grab-pool/', 'apps.application.urls_grab_pool'),
    ('demands/', 'apps.demand.urls'),
    ('announcements/', 'apps.announcement.urls'),
    ('positions/', 'apps.position.urls'),
    ('offers/', 'apps.offer.urls'),
    ('onboardings/', 'apps.onboarding.urls'),
    ('invitations/', 'apps.invitation.urls'),
    ('interviews/', 'apps.interview.urls'),
    ('referrals/', 'apps.referral.urls'),
    ('referral/', 'apps.referral.urls_single'),
    ('talent-pool/', 'apps.talent_pool.urls'),
    ('channels/', 'apps.channel.urls'),
    ('permissions-v2/', 'apps.mou.urls'),
    ('analytics/', 'apps.analytics.urls'),
    ('data/', 'apps.analytics.urls_data'),
    ('notifications/', 'apps.notification.urls'),
    ('audit-logs/', 'apps.audit.urls'),
    ('gdpr/', 'apps.gdpr.urls'),
    ('integrations/', 'apps.integration.urls'),
    ('campus/', 'apps.campus_control.urls'),
    ('campus-recruit/', 'apps.campus.urls'),
    ('external-sync/', 'apps.external_sync.urls'),
    ('dynamic-fields/', 'apps.dynamic_field.urls'),
    ('brand/', 'apps.brand.urls'),
    ('standard-resume/', 'apps.standard_resume.urls'),
    ('resumes/approval-flows/', 'apps.resume_flow.urls'),
    ('library/', 'apps.library.urls'),
    ('code-tables/', 'apps.code_table.urls'),
    ('scraped-resumes/', 'apps.scraped_resume.urls'),
    ('field-acl/', 'apps.field_acl.urls'),
    ('data-permissions/', 'apps.data_permission.urls'),
    ('rule-engine/', 'apps.rule_engine.urls'),
    ('metrics/', 'apps.metrics.urls'),
    ('duplicate-rules/', 'apps.duplicate_rule.urls'),
    ('reason-library/', 'apps.reason_library.urls'),
]

# 直接挂载的 APIView (非 include, 静态前缀)
_DIRECT_VIEWS = [
    ('system/config/demand', DemandConfigView.as_view()),
    ('background-check/callback', BackgroundCheckCallbackView.as_view(), 'bg-callback'),
    ('background-check/callback/', BackgroundCheckCallbackView.as_view()),
    ('background-check/orders/suppliers/', BackgroundCheckOrderViewSet.as_view({'get': 'suppliers'}), 'bg-orders-suppliers'),
    ('background-check/orders/products/', BackgroundCheckOrderViewSet.as_view({'get': 'products'}), 'bg-orders-products'),
    ('background-check/orders/create-order/', BackgroundCheckOrderViewSet.as_view({'post': 'create_order'}), 'bg-orders-create'),
    ('background-check/orders/', BackgroundCheckOrderViewSet.as_view({'get': 'list'}), 'bg-orders-list'),
    ('background-check/orders/<str:pk>/', BackgroundCheckOrderViewSet.as_view({'get': 'retrieve', 'post': 'cancel'}), 'bg-orders-detail'),
    ('background-check/orders/<str:pk>/query/', BackgroundCheckOrderViewSet.as_view({'get': 'query'}), 'bg-orders-query'),
    ('background-check/orders/<str:pk>/report/', BackgroundCheckOrderViewSet.as_view({'get': 'report'}), 'bg-orders-report'),
    ('media/upload/', MediaUploadView.as_view(), 'media-upload'),
    ('media/secure/<path:path>/', MediaDownloadView.as_view(), 'media-secure'),
]


def _build_api_v1_patterns():
    """#22: 由声明表构建 api_v1 路由, 非空前缀按长度降序, 消灭手工顺序敏感。"""
    patterns = []
    for _prefix, _mod in _FRONT_ORDERED + _EMPTY_PREFIX:
        patterns.append(path(_prefix, include(_mod)))
    for _prefix, _mod in sorted(_NON_EMPTY, key=lambda x: len(x[0]), reverse=True):
        patterns.append(path(_prefix, include(_mod)))
    for _entry in sorted(_DIRECT_VIEWS, key=lambda e: len(e[0]), reverse=True):
        if len(_entry) == 3:
            patterns.append(path(_entry[0], _entry[1], name=_entry[2]))
        else:
            patterns.append(path(_entry[0], _entry[1]))
    return patterns


api_v1_patterns = _build_api_v1_patterns()

# 2026-08-03 兵哥: admin token 从 env 读, 避免在 git 历史里漏.
# 设置 ADMIN_URL_TOKEN=<random> 在 .env, 不设则用 dev 默认 'ops-dashboard-7f3b9c2e' (跟旧版本兼容).
# 生产必须设, 部署时生成 secrets.token_urlsafe(24) 即可.
_ADMIN_URL_TOKEN = os.environ.get('ADMIN_URL_TOKEN') or 'ops-dashboard-7f3b9c2e'

urlpatterns = [
    path(f'{_ADMIN_URL_TOKEN}/', admin.site.urls),

    # API v1
    path('api/v1/', include((api_v1_patterns, 'v1'))),

    # API 文档
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # 健康检查
    path('health/', include('apps.core.urls_health')),
]

# 2026-06-28 花无缺: 前端 SPA fallback
#   Vite build 出的 web/app/dist/ 已经被 STATICFILES_DIRS 引入 (settings.base),
#   whitenoise 会从 STATIC_ROOT serve /static/* (asset js/css/font).
#   SPA 路由 (/candidates/123 /settings/users 这种深链) 会到 Django,
#   Django 没匹配 /api/ /<admin_token>/ /health/ /static/ 的路径全 fallthrough 到 index.html,
#   让前端 vue-router 处理 history 模式路由.
#
# ⚠️ 必须在 urlpatterns 最末尾 (在所有显式 path 之后) 才能 fallthrough
def spa_fallback(request, path=''):
    # 2026-06-29 拍平: 前端 dist 在 BASE_DIR.parent.parent / 'web' / 'app' / 'dist'
    #   BASE_DIR = /opt/ats/ATS-New/apps/django  →  父 x2 = /opt/ats/ATS-New
    index_file = settings.BASE_DIR.parent.parent / 'web' / 'app' / 'dist' / 'index.html'
    if index_file.exists():
        resp = FileResponse(open(index_file, 'rb'), content_type='text/html')
        # 🔴 2026-09-26: index.html 禁缓存。否则浏览器/边缘(CF)缓存旧 index.html →
        #   仍引用旧 hash 的 bundle，而 /version.json 是 no-store 实时取的 →
        #   「本地旧 bundle vs 线上新版本」永久 mismatch → 「系统已升级」弹窗反复弹、
        #   点「立即刷新」也不消失（刷新仍拿缓存里的旧文档）。
        resp['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    raise Http404(f'index.html not found at {index_file}')


def serve_version_json(request, path=''):
    """线上版本源：取 dist/version.json（与 dist/index.html 同一构建产物）。

    🔴 2026-09-26: 必须与 bundle 同源。此前若把 public/version.json（源码目录，
    任何 gen:version/typecheck/build 都会单独重写它）当作线上版本源，就会与已部署
    dist bundle 烙进的 APP_VERSION 失步（例：dist=62f8ab1 而 public=e016b1dc）→
    前端误判「有新版本」→ 无限弹窗。
    """
    version_file = settings.BASE_DIR.parent.parent / 'web' / 'app' / 'dist' / 'version.json'
    if version_file.exists():
        resp = FileResponse(open(version_file, 'rb'), content_type='application/json')
        resp['Cache-Control'] = 'no-store'
        return resp
    raise Http404(f'version.json not found at {version_file}')

urlpatterns += [
    # 线上版本源：显式路由，须排在 SPA catch-all 之前（否则会被 index.html 吃掉）
    path('version.json', serve_version_json),
    re_path(r'^(?P<path>(?!api/|health/|static/|media/|__debug__/).*)$', spa_fallback),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
