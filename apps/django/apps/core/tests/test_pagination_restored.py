"""P1-3 回归: 服务端分页 (StandardResultsSetPagination) 在审计点已恢复, 不可静默回退为 None。

参见 2026-10-08 代码审查报告 P1-3: 多个 ViewSet 曾被设为 `pagination_class = None`,
导致大列表无分页信封, 前端拿不到 `{count, next, previous, results}` 结构、也无法翻页。
本测试锁定"恢复"契约, 防止日后有人又把这些 ViewSet 改回无分页。

刻意豁免: library.SchoolViewSet / CompanyViewSet 保留 `pagination_class = None`,
因为前端 library.ts 用 n-data-table 客户端分页, 且依赖 `{success, data:[...]}` 信封契约。
这两处是明知决策, 反向断言其保持 None。
"""
from apps.announcement.views import AnnouncementViewSet
from apps.automation.views import AutomationTriggerView
from apps.common.pagination import StandardResultsSetPagination
from apps.core.views_permission_v2 import (
    ManagementUnitViewSet,
    PermissionResourceViewSet,
    PermissionTemplateViewSet,
    RoleViewSet,
    UserAppDataScopeViewSet,
    UserRoleViewSet,
)
from apps.library.views import MajorViewSet


def test_server_pagination_restored_on_audited_viewsets():
    """审计点列出的 ViewSet 必须启用服务端分页。"""
    assert AnnouncementViewSet.pagination_class is StandardResultsSetPagination
    assert MajorViewSet.pagination_class is StandardResultsSetPagination
    assert PermissionResourceViewSet.pagination_class is StandardResultsSetPagination
    assert PermissionTemplateViewSet.pagination_class is StandardResultsSetPagination
    assert RoleViewSet.pagination_class is StandardResultsSetPagination
    assert ManagementUnitViewSet.pagination_class is StandardResultsSetPagination
    assert UserRoleViewSet.pagination_class is StandardResultsSetPagination
    assert UserAppDataScopeViewSet.pagination_class is StandardResultsSetPagination
    assert AutomationTriggerView.pagination_class is StandardResultsSetPagination


def test_school_company_intentionally_keep_client_pagination():
    """反向断言: 这两个 ViewSet 刻意不启用服务端分页 (FE 客户端分页契约)。"""
    from apps.library.views import CompanyViewSet, SchoolViewSet

    assert SchoolViewSet.pagination_class is None
    assert CompanyViewSet.pagination_class is None
