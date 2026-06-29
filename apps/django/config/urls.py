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
    path('talent-pool/', include('apps.talent_pool.urls')),
    path('channels/', include('apps.channel.urls')),

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

    # 公共
    path('field-acl/', include('apps.field_acl.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),

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
#   Django 没匹配 /api/ /admin/ /health/ /static/ 的路径全 fallthrough 到 index.html,
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
    re_path(r'^(?P<path>(?!api/|admin/|health/|static/|__debug__/).*)$', spa_fallback),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
