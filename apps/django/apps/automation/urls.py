"""Automation URL Config - /api/v1/automation-rules/... (挂载点见 config/urls.py)

路由布局：
- /api/v1/automation-rules/trigger        AutomationTriggerView.create
- /api/v1/automation-rules/logs/          AutomationLogViewSet        (执行日志, 只读)
- /api/v1/automation-rules/logs/<pk>/     AutomationLogViewSet
- /api/v1/automation-rules/               AutomationRuleViewSet       (自动化规则)
- /api/v1/automation-rules/<pk>/          AutomationRuleViewSet
- /api/v1/automation-rules/<pk>/toggle/   AutomationRuleViewSet.toggle
- /api/v1/automation-rules/<pk>/logs/     AutomationRuleViewSet.logs  (单规则日志, 与上面的 logs/ 不冲突)
- /api/v1/automation-rules/<pk>/stats/    AutomationRuleViewSet.stats

⚠️ 修复记录 (2026-08-06 寇豆码): 原实现两个 ViewSet 都 register(r'')，
AutomationLogViewSet 的 list/detail 路由被先注册的 AutomationRuleViewSet 吃掉 → 不可达。
子资源前缀 `logs` 必须先于 r'' 注册。
注意 `^logs/<pk>/$`(日志详情) 与 `^<pk>/logs/$`(规则的日志 action) 段序不同，互不冲突。
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AutomationLogViewSet, AutomationRuleViewSet, AutomationTriggerView

router = DefaultRouter()
# 子资源前缀必须先注册：否则被 r'' 的 `^(?P<pk>[^/.]+)/$` 当 pk='logs' 吃掉
router.register(r'logs', AutomationLogViewSet, basename='automation-log')
router.register(r'', AutomationRuleViewSet, basename='automation-rule')

trigger_view = AutomationTriggerView.as_view({'post': 'create'})

urlpatterns = [
    path('trigger', trigger_view, name='automation-trigger'),
    path('', include(router.urls)),
]
