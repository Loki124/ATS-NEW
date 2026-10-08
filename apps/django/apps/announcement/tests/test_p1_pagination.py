"""P1-Fix3 回归锁: 服务端分页恢复 (per P1 audit).

修复前: AnnouncementViewSet / 各 permission_v2 ViewSet / MajorViewSet / registration_list 等
把 pagination_class 置为 None, list 返回裸 data list, 前端被迫自行分页且丢失分页元信息.

修复后: 这些端点恢复 StandardResultsSetPagination, list 走 paginate_queryset /
get_paginated_response, 响应顶层含 pagination 键 ({page,page_size,total,...} 信封).

本文件锁定"公告 list 返回分页信封"这一可观察行为, 并附一条轻量的 view 类属性断言.
"""
import pytest

from apps.announcement.models import Announcement
from apps.announcement.views import AnnouncementViewSet
from apps.common.pagination import StandardResultsSetPagination


@pytest.mark.django_db
def test_announcement_list_returns_paginated_envelope(auth_client):
    """Fix3: 公告 list 恢复服务端分页, 响应含顶层 pagination 键而非裸 list."""
    Announcement.objects.create(
        title='P1-分页锁', category='SYSTEM', audience='RECRUIT_EXPERT',
        body='b', is_active=True)
    resp = auth_client.get('/api/v1/announcements/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body.get('success') is True
    # data 仍是 list (FE 兼容), 但顶层多了 pagination 信封
    assert isinstance(body.get('data'), list)
    assert 'pagination' in body
    assert isinstance(body['pagination'], dict)
    assert 'total' in body['pagination']
    assert 'page' in body['pagination']


def test_announcement_viewset_pagination_class_set():
    """Fix3(轻量): AnnouncementViewSet 显式设置 StandardResultsSetPagination
    (若鉴权搭建过重, 至少锁住配置属性不回退为 None)."""
    assert AnnouncementViewSet.pagination_class is StandardResultsSetPagination
