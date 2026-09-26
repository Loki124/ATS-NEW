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
from apps.common.views import MediaUploadView
from apps.demand.views import DemandConfigView
# 2026-08-28 寇豆码: 背调供应商异步回调入向端点（§5.2 验签，供应商签名保护，不鉴权）
from apps.integration.views import BackgroundCheckCallbackView, BackgroundCheckOrderViewSet

api_v1_patterns = [
    # 全局统一搜索 (Plan P): 必须排在 urls_stubs 的 search stub 之前以优先命中
    # (urls_stubs 挂在 '' 上内含 path('search/', global_search), 若在其后会被 stub 抢先)
    path('search/', include('apps.search.urls')),
    # 认证
    path('auth/', include('apps.core.urls_auth')),
    # 2026-09-08: 面试轮次真实端点，必须挂在 urls_stubs 之前覆盖 stub
    #   urls_round 内部已包含 recruitment-rounds 前缀
    path('', include('apps.process.urls_round')),
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
    # 2026-09-26: 阶段类型枚举别名前缀。前端 api/dictionary.ts:132 按契约调
    #   /api/v1/recruitment-stages/stage-types/，但 RecruitmentStageViewSet 原只挂在 /stages/。
    #   加此别名（同指 urls_stage）使既有前端契约可达，无需改前端。
    path('recruitment-stages/', include('apps.process.urls_stage')),
    path('processes/', include('apps.process.urls_process')),
    path('process-stage-links/', include('apps.process.urls_link')),
    # 2026-06-17: G38 — 挂载已写好但未注册的 ViewSet (FE recruitment-process.ts 直接用到)
    path('stage-rules/', include('apps.process.urls_rule')),
    # 2026-09-08: 对齐 SPEC-stage-rule-config.md + FE recruitment-process.ts 已进入条件规则统一前缀
    #   /api/v1/entry-condition-rules/（原 recruitment-rules/entry-conditions/ 为迁移前旧路径，FE 早已切到新前缀，
    #   BE 挂载未同步导致 create/list/toggle/reorder/evaluate 全 404）
    path('entry-condition-rules/', include('apps.entry_condition.urls')),
    # 2026-06-17: G38 — 新挂 3 个 alias APIView (覆盖 FE 调用的 stageId/candidateId 路径变体)
    path('time-limit-rules/', include('apps.time_limit.urls')),
    path('automation-rules/', include('apps.automation.urls')),
    path('expressions/', include('apps.process.urls_expression')),

    # 业务域
    path('candidates/', include('apps.candidate.urls')),
    path('candidates/add-candidate/', include(('apps.add_candidate.urls', 'add_candidate'))),
    path('applications/', include('apps.application.urls')),
    # 2026-08-06 寇豆码: GrabPoolViewSet 原来与 ApplicationViewSet 共用同一个 router 且都
    #   register(r''), `^$`/`^summary/$`/`^reassign/$` 全被 ApplicationViewSet 的
    #   `^$` 和 `^(?P<id>[^/.]+)/$` 吃掉 → 整块不可达. 拆独立 URLconf 并按
    #   apps/application/views.py docstring 声明的契约挂顶层 /api/v1/grab-pool/
    #   (挂 applications/ 之下会与 /api/v1/applications/{id}/grab/ 语义混淆).
    path('grab-pool/', include('apps.application.urls_grab_pool')),
    path('demands/', include('apps.demand.urls')),
    # 2026-08-24: 招聘需求设置全局配置端点 (FE DemandConfig.vue)
    #   GET/POST/PUT /api/v1/system/config/demand  → DemandConfigView
    path('system/config/demand', DemandConfigView.as_view()),
    path('announcements/', include('apps.announcement.urls')),
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
    # 2026-08-24: G35 数据中心 KPI + 订阅 — FE api/data.ts 调 /data/kpi, /data/subscriptions
    #   (KpiViewSet / DataSubscriptionViewSet 此前已实现但漏挂路由, 导致 404)
    path('data/', include('apps.analytics.urls_data')),
    # 2026-06-17: G35 数据看板 KPI — FE api/data.ts:48 调 /data/kpi
    # 2026-06-17: G35 数据订阅 — FE api/data.ts:57 调 /data/subscriptions

    # 通知 / 审计 / GDPR / 集成
    path('notifications/', include('apps.notification.urls')),
    path('audit-logs/', include('apps.audit.urls')),
    path('gdpr/', include('apps.gdpr.urls')),
    path('integrations/', include('apps.integration.urls')),
    # 2026-08-28 寇豆码: 背调供应商异步回调（§5.2 验签）。供应商入向端点，放在 integrations 之后单独挂，
    #   前缀 background-check/ 不与 integrations router 冲突；不加 IsSuperAdmin，靠签名保护。
    path('background-check/callback', BackgroundCheckCallbackView.as_view(), name='bg-callback'),
    path('background-check/callback/', BackgroundCheckCallbackView.as_view()),
    # 2026-08-28 寇豆码: 背调订单状态机视图（超管可读 + 取消）。与 callback 同前缀但路径无冲突。
    path('background-check/orders/', BackgroundCheckOrderViewSet.as_view({'get': 'list'}), name='bg-orders-list'),
    path('background-check/orders/<str:pk>/', BackgroundCheckOrderViewSet.as_view({'get': 'retrieve', 'post': 'cancel'}), name='bg-orders-detail'),
    # T6 新增接口: 轮询订单最新状态 / 拉取报告（与 cancel 同前缀，detail 子路由）
    path('background-check/orders/<str:pk>/query/', BackgroundCheckOrderViewSet.as_view({'get': 'query'}), name='bg-orders-query'),
    path('background-check/orders/<str:pk>/report/', BackgroundCheckOrderViewSet.as_view({'get': 'report'}), name='bg-orders-report'),
    # 2026-08-17 PR #69: 数据字典 (apps.dictionary) — 业务自定语义枚举 single source of truth.
    #   注: 阶段类型已改为系统内置枚举 (apps.process.models.StageType), 经迁移预置起止阶段,
    #   不再经 dictionary-items/dictionary-types 暴露 recruitment_stage_type.
    #   router 注册 dictionary-items / dictionary-types, 挂在 api_v1 根下 →
    #   /api/v1/dictionary-items/
    #   /api/v1/dictionary-types/
    path('', include('apps.dictionary.urls')),
    # 2026-08-20: 校招管控（人员比例管控系统）— 规则 / 人员 / 看板 / 规划 / 校验
    path('campus/', include('apps.campus_control.urls')),
    # 2026-09-23 Phase 4: 校招专属功能（校园大使 + 宣讲会）。
    #   /api/v1/campus/ 已被 campus_control 占用，故独立前缀 campus-recruit/。
    #   模型 recruit_type 默认 campus，经 ScopeQuerysetMixin 自动隔离。
    path('campus-recruit/', include('apps.campus.urls')),

    # Phase 2 T02 (寇豆码): 原删 'external-sync'/'data' 空壳 URL 挂载; 二者 FE 仍真实调用, 已重建:
    #   data  -> analytics/urls_data.py (/data/kpi, /data/subscriptions)
    #   external-sync -> apps.external_sync (G40 Mock 占位端点, 无 model)
    path('external-sync/', include('apps.external_sync.urls')),
    #   scraped_resume 是真实功能, 保留 (FE 真实调用)!
    #   scraped-resumes: T02.5 落地最小 model, G30 完整功能由 T06
    #   duplicate-check: 已于 2026-09-05 删除 (G45 查重已迁 apps.add_candidate, stub 假绿)
    path('dynamic-fields/', include('apps.dynamic_field.urls')),
    # 2026-09-10 寇豆码: G43 品牌信息管理 — 单例配置端点 /api/v1/brand/ (GET 读 / PUT/PATCH 改)
    path('brand/', include('apps.brand.urls')),
    # 2026-09-09: 标准简历配置落库端点（FE StandardResumeSettings.vue）
    #   GET/POST/PUT /api/v1/standard-resume/ → StandardResumeConfigView（单体 JSON 配置）
    path('standard-resume/', include('apps.standard_resume.urls')),
    path('resumes/approval-flows/', include('apps.resume_flow.urls')),
    path('library/', include('apps.library.urls')),
    # 2026-09-14: G46 码表库（行政区划 / 国家区号 / 民族 / 语言）
    path('code-tables/', include('apps.code_table.urls')),
    path('scraped-resumes/', include('apps.scraped_resume.urls')),

    # 公共
    path('media/upload/', MediaUploadView.as_view(), name='media-upload'),
    path('field-acl/', include('apps.field_acl.urls')),
    # 2026-09-15: 字段权限（列级字段权限, 按 角色/部门/用户 维度）— 管理面 CRUD
    path('data-permissions/', include('apps.data_permission.urls')),
    # 2026-08-31: Phase 1 统一规则引擎只读 API（适配器读路径，零改动 legacy 写路径）
    path('rule-engine/', include('apps.rule_engine.urls')),
    # 2026-09-25: 指标库（规则引擎指标层：原子/派生指标 + 模板 + 一次性执行）
    path('metrics/', include('apps.metrics.urls')),
    # 2026-09-13: 重复候选人管理（合并规则 / 重复申请管理 / 候选人查重规则）
    #   GET         /api/v1/duplicate-rules/catalog/
    #   GET|PUT     /api/v1/duplicate-rules/config/
    #   GET|POST    /api/v1/duplicate-rules/rules/
    #   GET|PUT|DEL /api/v1/duplicate-rules/rules/<pk>/
    #   POST        /api/v1/duplicate-rules/rules/<pk>/toggle/
    #   POST        /api/v1/duplicate-rules/rules/reset/
    path('duplicate-rules/', include('apps.duplicate_rule.urls')),
    # Phase 2 T01 (寇豆码): 原因库 — 标签池 + 场景规则
    #   /api/v1/reason-library/tags/         标签 CRUD + CSV 导入
    #   /api/v1/reason-library/rules/        规则 CRUD + JSON 导入导出 + snapshot
    #   /api/v1/reason-library/scenes/       场景全局绑定
    #   /api/v1/reason-library/active/       业务态查询
    #   /api/v1/reason-library/rules/<pk>/wizard/save/  三步原子保存
    path('reason-library/', include('apps.reason_library.urls')),
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
    re_path(r'^(?P<path>(?!api/|health/|static/|media/|__debug__/).*)$', spa_fallback),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
