"""路由掩盖回归测试 — 锁死 2026-08-06 的 8 处 DefaultRouter 路由掩盖修复.

背景: DRF DefaultRouter 上若两个 ViewSet 都 `register(r'')`, 后注册的
list(^$)/detail(^(?P<pk>...)/$) 路由会被先注册的吃掉, 导致子资源 ViewSet
永远不可达. 本次修复把"被吃掉"的 ViewSet 改挂到独立前缀 (costs/logs/exports/
sync-logs/tags/evaluations), 并把 GrabPoolViewSet 拆到顶层 /api/v1/grab-pool/.

本测试用 Django 的 `resolve()` 逐一断言:
  1. 原"可达"路径仍由**原 ViewSet** 服务 (未被破坏);
  2. 原"被吃"路径现在由**正确的子资源 ViewSet** 服务 (修复生效).

若有人不慎把子资源 ViewSet 重新 `register(r'')`, 这里会立刻失败, 防止掩盖复发.
"""
from __future__ import annotations

import pytest
from django.urls import Resolver404, resolve


def _viewset_name(path: str) -> str:
    """对给定 URL 做 resolve(), 返回服务的 ViewSet 类名.

    若 Resolver404 直接抛 pytest.fail, 因为被吃端点现在**必须**可达.
    """
    try:
        match = resolve(path)
    except Resolver404:
        pytest.fail(f'路由掩盖未修复: {path} 仍然无匹配 (Resolver404)')
    cls = getattr(match.func, 'cls', None)
    if cls is not None:
        return cls.__name__
    # @action / 普通 View: 退回 view_class / 函数名
    return getattr(match.func, 'view_class', None).__name__ or match.func.__name__


# (路径, 期望服务的 ViewSet 类名)
# 注意: 这里同时覆盖"原可达"与"被吃后修复可达"两类路径.
EXPECTED_ROUTES = [
    # 1. channel -----------------------------------------------------------
    ('/api/v1/channels/', 'ChannelViewSet'),                 # 原可达, 不变
    ('/api/v1/channels/costs/', 'ChannelCostViewSet'),        # 被吃 → 现可达
    ('/api/v1/channels/costs/1/', 'ChannelCostViewSet'),      # detail
    # 2. notification ------------------------------------------------------
    ('/api/v1/notifications/', 'NotificationTemplateViewSet'),  # 原可达, 不变
    ('/api/v1/notifications/logs/', 'NotificationLogViewSet'),   # 被吃 → 现可达
    ('/api/v1/notifications/logs/unread/', 'NotificationLogViewSet'),
    # 3. automation -------------------------------------------------------
    ('/api/v1/automation-rules/', 'AutomationRuleViewSet'),   # 原可达, 不变
    ('/api/v1/automation-rules/logs/', 'AutomationLogViewSet'),  # 被吃 → 现可达
    # 4. analytics ---------------------------------------------------------
    ('/api/v1/analytics/', 'ReportSnapshotViewSet'),          # 原可达, 不变
    ('/api/v1/analytics/exports/', 'ExportTaskViewSet'),       # 被吃 → 现可达
    ('/api/v1/analytics/exports/dashboard-summary/', 'ExportTaskViewSet'),
    # 5. integration -------------------------------------------------------
    ('/api/v1/integrations/', 'IntegrationConfigViewSet'),    # 原可达, 不变
    ('/api/v1/integrations/sync-logs/', 'IntegrationSyncLogViewSet'),  # 被吃→现可达
    # 6. talent_pool -------------------------------------------------------
    ('/api/v1/talent-pool/', 'TalentPoolEntryViewSet'),       # 原可达, 不变
    ('/api/v1/talent-pool/tags/', 'TalentPoolTagViewSet'),     # 被吃 → 现可达
    # 7. interview ---------------------------------------------------------
    ('/api/v1/interviews/', 'InterviewViewSet'),              # 原可达, 不变
    ('/api/v1/interviews/evaluations/', 'InterviewEvaluationViewSet'),  # 被吃→现可达
    # 8. application / grab-pool ------------------------------------------
    ('/api/v1/applications/', 'ApplicationViewSet'),          # 原可达, 不变
    ('/api/v1/grab-pool/', 'GrabPoolViewSet'),                # 被吃 → 现可达 (独立 router)
    ('/api/v1/grab-pool/summary/', 'GrabPoolViewSet'),
    ('/api/v1/grab-pool/reassign/', 'GrabPoolViewSet'),
]


@pytest.mark.parametrize('path,expected_viewset', EXPECTED_ROUTES)
def test_route_not_masked(path: str, expected_viewset: str) -> None:
    """逐路径断言路由未被掩盖, 且由正确的 ViewSet 服务."""
    actual = _viewset_name(path)
    assert actual == expected_viewset, (
        f'{path} 应由 {expected_viewset} 服务, '
        f'实际解析到 {actual} (路由掩盖可能复发)'
    )


def test_grab_pool_is_separate_from_application() -> None:
    """GrabPoolViewSet 必须挂顶层 /api/v1/grab-pool/, 而非被 ApplicationViewSet 吞掉."""
    grab = _viewset_name('/api/v1/grab-pool/')
    app = _viewset_name('/api/v1/applications/')
    assert grab == 'GrabPoolViewSet'
    assert app == 'ApplicationViewSet'
    assert grab != app
