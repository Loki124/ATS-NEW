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

api_v1_patterns = [
    # 认证
    path('auth/', include('apps.core.urls_auth')),
    # 2026-07-01 花无缺: 把 urls_stubs 挂到 core.urls 之前, 避免 core/permissions router 抢
    #   /permissions/{roles,functions,menus,user-info,permissions/list} 这些 stub path
    #   (之前 line 60, 被 core 的 router.register(r'permissions', ...) 抢先吃掉)
    path('', include('apps.referral.urls_stubs')),
    # 2026-07-12 花无缺: V2 权限系统 9 endpoints 必须在 core.urls 之前注册 —
    #   core.urls 的 router.register(r'permissions', ...) 抢 '^permissions/<pk>/$' 会
    #   把 V2 的 /api/v1/permissions/resources/ 当 pk=resources 吃掉 (404). 先注册 V2 让
    #   长前缀 (resources/templates) 优先 match.
    path('', include('apps.core.urls_permission_v2')),
    # 2026-06-17: G41 用户管理 + 组织架构 + 角色 + 权限码 4 个 ViewSet (apps/core/urls.py)
    # 挂到 '' 上: users→/api/v1/users/  departments→/api/v1/departments/  roles→/api/v1/roles/  permissions→/api/v1/permissions/
    path('', include('apps.core.urls')),

    # 流程域
    path('stages/', include('apps.process.urls_stage')),
    path('processes/', include('apps.process.urls_process')),
    # 2026-06-17: 旧前缀别名 (FE recruitment-process.ts 之前用 /recruitment-processes/, 之后重命名到 /processes/,
    # 但 4 个模板页面里可能还有旧 URL 残留; 留个 alias 不影响)
    path('recruitment-processes/', include('apps.process.urls_process')),
    path('process-stage-links/', include('apps.process.urls_link')),
    path('recruitment-process-stage-links/', include('apps.process.urls_link')),
    # 2026-06-17: G38 — 挂载已写好但未注册的 ViewSet (FE recruitment-process.ts 直接用到)
    path('stage-rules/', include('apps.process.urls_rule')),
    path('recruitment-rules/entry-conditions/', include('apps.entry_condition.urls')),
    path('entry-condition-rules/', include('apps.entry_condition.urls')),  # 旧前缀别名
    # 2026-06-17: G38 — 新挂 3 个 alias APIView (覆盖 FE 调用的 stageId/candidateId 路径变体)
    path('time-limit-rules/', include('apps.time_limit.urls')),
    path('automation-rules/', include('apps.automation.urls')),
    path('expressions/', include('apps.process.urls_expression')),

    # 业务域
    path('candidates/', include('apps.candidate.urls')),
    path('candidates/add-candidate/', include(('apps.add_candidate.urls', 'add_candidate'))),
    path('applications/', include('apps.application.urls')),
    path('demands/', include('apps.demand.urls')),
    path('positions/', include('apps.position.urls')),
    path('offers/', include('apps.offer.urls')),
    path('onboardings/', include('apps.onboarding.urls')),
    path('invitations/', include('apps.invitation.urls')),
    path('interviews/', include('apps.interview.urls')),
    path('referrals/', include('apps.referral.urls')),
    # 2026-07-01 花无缺: FE referral.ts 误用单数 /referral/, 加 alias
    #   /referral/codes/me  →  /referrals/codes/me
    #   /referral/records/me  →  /referrals/my-referrals (records/me → my-referrals)
    #   /referral/rules  →  /referrals/ (list 空, rules 待 G36 实现)
    #   /referral/expert-configs/me  →  /referrals/ (暂无)
    #   /referral/records  →  /referrals/
    #   /referral/records/me/summary  →  /referrals/my-referrals (stats stub)
    #   /referral/rewards/me  →  /referrals/ (暂无, 返空)
    path('referral/', include('apps.referral.urls_single')),
    # 2026-07-01 花无缺: FE 调用了但 backend 缺实现的 22 个 endpoint 一次性 stub
    #   auth/register, auth/change-password, candidates/batch/*, recruitment-rules/*,
    #   recruitment-rounds/*, bulk-create, upload-and-parse, scoring/start,
    #   offer-templates, search, evaluate, login (单数 alias), duplicate-check/ list
    # 详细 stub 逻辑在 apps.referral.urls_stubs (寄放 referral app, 仅是位置)
    # 2026-07-01 update: urls_stubs 已挂到顶部 (line 21) 在 core.urls 之前, 避免被 permissions router 抢
    # path('', include('apps.referral.urls_stubs')),
    path('talent-pool/', include('apps.talent_pool.urls')),
    path('channels/', include('apps.channel.urls')),
    # 2026-07-01 花无缺: G36 — MOU 业务从 stub 升级到真 app
    #   之前走 stub (apps.referral.urls_stubs.permissions_v2_*), 路由优先级: stub 先挂 → mou 真接
    #   删 stub 的 permissions-v2/* 5 个 path, 改挂 mou app (4 个 ViewSet + 1 stub audit-logs)
    path('permissions-v2/', include('apps.mou.urls')),

    # 数据中心
    path('analytics/', include('apps.analytics.urls')),
    # 2026-06-17: G35 数据看板 KPI — FE api/data.ts:48 调 /data/kpi
    # 2026-06-17: G35 数据订阅 — FE api/data.ts:57 调 /data/subscriptions

    # 通知 / 审计 / GDPR / 集成
    path('notifications/', include('apps.notification.urls')),
    path('audit-logs/', include('apps.audit.urls')),
    path('gdpr/', include('apps.gdpr.urls')),
    path('integrations/', include('apps.integration.urls')),
    # 2026-06-17: G30 RPA — FE api/scraped-resume.ts:34 调 /scraped-resumes
    # 2026-06-17: G41 数据字典 — FE 用 by-type/{type}/ 拿枚举值

    # Phase 2 T02 (寇豆码): 删 'external-sync'/'data' 两个 0-model 空壳 URL 挂载.
    #   scraped_resume / duplicate_check 是真实功能, 保留 (FE 真实调用)!
    #   scraped-resumes: T02.5 落地最小 model, G30 完整功能由 T06
    #   duplicate-check: 7 处前端调用, T02.4 保留
    path('dynamic-fields/', include('apps.dynamic_field.urls')),
    path('resumes/approval-flows/', include('apps.resume_flow.urls')),
    path('library/', include('apps.library.urls')),
    path('scraped-resumes/', include('apps.scraped_resume.urls')),
    path('duplicate-check/', include('apps.duplicate_check.urls')),

    # 公共
    path('field-acl/', include('apps.field_acl.urls')),
]

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
        return FileResponse(open(index_file, 'rb'), content_type='text/html')
    raise Http404(f'index.html not found at {index_file}')

urlpatterns += [
    re_path(r'^(?P<path>(?!api/|health/|static/|__debug__/).*)$', spa_fallback),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
