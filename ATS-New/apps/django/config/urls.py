"""URL 路由总入口"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

api_v1_patterns = [
    # 认证
    path('auth/', include('apps.core.urls_auth')),

    # 流程域
    path('stages/', include('apps.process.urls_stage')),
    path('processes/', include('apps.process.urls_process')),
    path('process-stage-links/', include('apps.process.urls_link')),
    path('entry-condition-rules/', include('apps.entry_condition.urls')),
    path('time-limit-rules/', include('apps.time_limit.urls')),
    path('automation-rules/', include('apps.automation.urls')),
    path('expressions/', include('apps.process.urls_expression')),

    # 业务域
    path('candidates/', include('apps.candidate.urls')),
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

    # 通知 / 审计 / GDPR / 集成
    path('notifications/', include('apps.notification.urls')),
    path('audit-logs/', include('apps.audit.urls')),
    path('gdpr/', include('apps.gdpr.urls')),
    path('integrations/', include('apps.integration.urls')),

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

    # Prometheus
    path('', include('django_prometheus.urls')) if getattr(settings, 'PROMETHEUS_ENABLED', False) else path('', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
