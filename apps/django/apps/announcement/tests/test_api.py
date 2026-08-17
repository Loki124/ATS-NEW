"""制度公告 API 测试 — 读放开 / 写需 HR 及以上 / 软删 / 置顶排序 / 配置与概述。"""
import pytest
from rest_framework.test import APIClient

from apps.announcement.models import Announcement, AnnouncementConfig

URL = '/api/v1/announcements/'
CONFIG_URL = '/api/v1/announcements/config/'


@pytest.mark.django_db
class TestAnnouncementAPI:
    def test_list_requires_auth(self):
        """未登录读 → 401。"""
        client = APIClient()
        resp = client.get(URL)
        assert resp.status_code == 401

    def test_hr_lists_active_only_by_default(self, auth_hr_client):
        """HR 读列表默认仅上架；下架项不出现。"""
        Announcement.objects.create(title='A上架', category='SYSTEM', audience='RECRUIT_EXPERT', body='x', is_active=True)
        Announcement.objects.create(title='B下架', category='NOTICE', audience='RECRUIT_EXPERT', body='x', is_active=False)

        resp = auth_hr_client.get(URL)
        assert resp.status_code == 200
        titles = [d['title'] for d in resp.json()['data']]
        assert 'A上架' in titles
        assert 'B下架' not in titles

    def test_show_inactive_includes_taken_down(self, auth_hr_client):
        """管理页传 show_inactive=true 连下架项一并展示。"""
        Announcement.objects.create(title='C上架', category='SYSTEM', audience='RECRUIT_EXPERT', body='x', is_active=True)
        Announcement.objects.create(title='D下架', category='NOTICE', audience='RECRUIT_EXPERT', body='x', is_active=False)

        resp = auth_hr_client.get(URL + '?show_inactive=true')
        assert resp.status_code == 200
        titles = [d['title'] for d in resp.json()['data']]
        assert 'C上架' in titles and 'D下架' in titles

    def test_pinned_orders_first(self, auth_hr_client):
        """置顶项排在最前。"""
        Announcement.objects.create(title='普通', category='SYSTEM', audience='RECRUIT_EXPERT', body='x', pinned=False)
        Announcement.objects.create(title='置顶', category='NOTICE', audience='RECRUIT_EXPERT', body='x', pinned=True)

        resp = auth_hr_client.get(URL)
        assert resp.json()['data'][0]['title'] == '置顶'

    def test_hr_can_create(self, auth_hr_client, hr_user):
        """HR 创建 → 201，字段落库且 created_by 为当前用户。"""
        payload = {
            'title': '新制度',
            'category': 'SYSTEM',
            'audience': 'RECRUIT_EXPERT',
            'body': '正文内容',
        }
        resp = auth_hr_client.post(URL, payload, format='json')
        assert resp.status_code == 201, resp.content
        obj = Announcement.objects.get(title='新制度')
        assert obj.category == 'SYSTEM'
        assert obj.audience == 'RECRUIT_EXPERT'
        assert obj.created_by_id == hr_user.id

    def test_non_hr_cannot_create(self, api_client):
        """非 HR 创建 → 403（写操作门禁）。"""
        from django.contrib.auth import get_user_model
        plain = get_user_model().objects.create_user(username='plain', password='x')
        api_client.force_authenticate(user=plain)
        resp = api_client.post(URL, {
            'title': '越权', 'category': 'SYSTEM', 'audience': 'RECRUIT_EXPERT', 'body': 'x',
        }, format='json')
        assert resp.status_code == 403

    def test_soft_delete_hides_from_list(self, auth_hr_client):
        """HR 删除 → 204，软删后列表不再出现。"""
        obj = Announcement.objects.create(title='待删', category='SYSTEM', audience='RECRUIT_EXPERT', body='x')
        del_resp = auth_hr_client.delete(f'{URL}{obj.id}/')
        assert del_resp.status_code == 204
        # 软删：DB 行仍在，但列表过滤 deleted_at__isnull 排除
        assert Announcement.objects.filter(id=obj.id).exists()
        assert Announcement.objects.filter(id=obj.id, deleted_at__isnull=True).exists() is False
        titles = [d['title'] for d in auth_hr_client.get(URL).json()['data']]
        assert '待删' not in titles

    # ===== 概述 summary 字段 =====
    def test_summary_roundtrip(self, auth_hr_client):
        """创建带 summary，列表与详情序列化器均应回传 summary。"""
        payload = {
            'title': '带概述', 'category': 'SYSTEM', 'audience': 'RECRUIT_EXPERT',
            'summary': '这是概述', 'body': '这是正文',
        }
        create = auth_hr_client.post(URL, payload, format='json')
        assert create.status_code == 201, create.content
        obj = Announcement.objects.get(title='带概述')
        assert obj.summary == '这是概述'
        # 列表信封含 summary
        list_resp = auth_hr_client.get(URL).json()['data']
        assert any(d['title'] == '带概述' and d['summary'] == '这是概述' for d in list_resp)

    # ===== 模块配置：工作台模块总开关 =====
    def test_config_get_default(self, auth_hr_client):
        """GET 配置默认 show_on_workbench=True（单条公告展示位置由自身字段决定）。"""
        resp = auth_hr_client.get(CONFIG_URL)
        assert resp.status_code == 200
        # 渲染器输出为驼峰；配置仅含模块总开关
        data = resp.json()['data']
        assert data['showOnWorkbench'] is True
        assert 'showInMore' not in data
        assert AnnouncementConfig.objects.filter(pk=1).exists()

    def test_config_put_requires_hr(self, api_client):
        """非 HR 修改配置 → 403。"""
        from django.contrib.auth import get_user_model
        plain = get_user_model().objects.create_user(username='plain2', password='x')
        api_client.force_authenticate(user=plain)
        resp = api_client.put(CONFIG_URL, {'show_on_workbench': False}, format='json')
        assert resp.status_code == 403

    def test_config_put_updates_and_persists(self, auth_hr_client):
        """HR 关闭工作台模块，GET 与 DB 均反映。"""
        put = auth_hr_client.put(CONFIG_URL, {'show_on_workbench': False}, format='json')
        assert put.status_code == 200
        data = put.json()['data']
        assert data['showOnWorkbench'] is False
        # 再次读取保持
        again = auth_hr_client.get(CONFIG_URL).json()['data']
        assert again['showOnWorkbench'] is False
        cfg = AnnouncementConfig.objects.get(pk=1)
        assert cfg.show_on_workbench is False

    # ===== 单条公告展示位置（两个独立开关）=====
    def test_announcement_display_flags_default_and_persist(self, auth_hr_client):
        """创建带展示位置开关的公告，序列化与 DB 均反映。"""
        payload = {
            'title': '展示位置测试', 'category': 'SYSTEM', 'audience': 'RECRUIT_EXPERT',
            'body': '正文', 'show_on_workbench': False, 'show_in_more': True,
        }
        create = auth_hr_client.post(URL, payload, format='json')
        assert create.status_code == 201, create.content
        data = create.json()['data']
        assert data['showOnWorkbench'] is False
        assert data['showInMore'] is True
        obj = Announcement.objects.get(title='展示位置测试')
        assert obj.show_on_workbench is False
        assert obj.show_in_more is True

    def test_announcement_display_flags_default_values(self, auth_hr_client):
        """未传展示开关时，show_on_workbench=True；已发布公告 show_in_more=True。"""
        obj = Announcement.objects.create(
            title='默认位置', category='SYSTEM', audience='RECRUIT_EXPERT', body='x',
        )
        assert obj.show_on_workbench is True
        assert obj.show_in_more is True
        resp = auth_hr_client.get(f'{URL}{obj.id}/')
        data = resp.json()['data']
        assert data['showOnWorkbench'] is True
        assert data['showInMore'] is True

    def test_partial_update_display_flags(self, auth_hr_client):
        """仅 PATCH 展示开关，其余字段不被清空。"""
        obj = Announcement.objects.create(
            title='改位置', category='SYSTEM', audience='RECRUIT_EXPERT',
            summary='概述', body='正文', is_active=True,
        )
        resp = auth_hr_client.patch(f'{URL}{obj.id}/', {'show_on_workbench': False, 'show_in_more': True}, format='json')
        assert resp.status_code == 200, resp.content
        obj.refresh_from_db()
        assert obj.show_on_workbench is False
        assert obj.show_in_more is True
        # 其余字段保持不变
        assert obj.title == '改位置'
        assert obj.body == '正文'

    # ===== 推送记录 =====
    def test_push_creates_record_and_notifications(self, auth_hr_client, hr_user):
        """HR 推送公告 → 创建推送记录并发送站内信通知。"""
        obj = Announcement.objects.create(
            title='推送测试', category='NOTICE', audience='RECRUIT_EXPERT',
            body='正文', is_active=True,
        )
        resp = auth_hr_client.post(f'{URL}{obj.id}/push/', {'channel': 'IN_APP'}, format='json')
        assert resp.status_code == 201, resp.content
        data = resp.json()['data']
        assert data['totalCount'] >= 1  # hr_user 在受众内
        assert data['pushedByName'] == hr_user.username
        # retrieve 返回 pushRecords
        get_resp = auth_hr_client.get(f'{URL}{obj.id}/')
        records = get_resp.json()['data']['pushRecords']
        assert len(records) == 1
        assert records[0]['readCount'] == 0
        assert records[0]['unreadCount'] >= 1

    def test_notify_unread_resends_to_unread(self, auth_hr_client):
        """通知未读人员 → 未读数为 0 时返回 400。"""
        obj = Announcement.objects.create(
            title='提醒测试', category='NOTICE', audience='RECRUIT_EXPERT',
            body='正文', is_active=True,
        )
        push = auth_hr_client.post(f'{URL}{obj.id}/push/', {'channel': 'IN_APP'}, format='json')
        push_id = push.json()['data']['id']
        # 取出本次推送产生的通知日志 id，全部标记为已读后再提醒应无未读人员
        from apps.announcement.models import AnnouncementPushRecord
        from apps.notification.models import NotificationLog
        rec = AnnouncementPushRecord.objects.get(id=push_id)
        log_ids = (rec.context or {}).get('log_ids', [])
        NotificationLog.objects.filter(id__in=log_ids).update(read_at='2026-01-01T00:00:00Z')
        remind = auth_hr_client.post(f'{URL}{obj.id}/push/{push_id}/notify-unread/', {}, format='json')
        assert remind.status_code == 400
        assert '已无未读' in remind.json()['detail']

    # ===== 更新（PATCH 局部更新，支持只改上架开关）=====
    def test_partial_update_toggle_active(self, auth_hr_client):
        """仅发 is_active 的 PATCH 应 200，且其余字段不被清空（开关场景）。"""
        obj = Announcement.objects.create(
            title='开关测试', category='SYSTEM', audience='RECRUIT_EXPERT',
            summary='概述', body='正文', is_active=True,
        )
        resp = auth_hr_client.patch(f'{URL}{obj.id}/', {'is_active': False}, format='json')
        assert resp.status_code == 200, resp.content
        obj.refresh_from_db()
        assert obj.is_active is False
        # 其余字段保持不变
        assert obj.title == '开关测试'
        assert obj.body == '正文'

    def test_full_update_via_patch(self, auth_hr_client):
        """PATCH 携带全量可编辑字段 → 200 且字段更新。"""
        obj = Announcement.objects.create(
            title='旧标题', category='SYSTEM', audience='RECRUIT_EXPERT',
            summary='旧概述', body='旧正文', is_active=True,
        )
        resp = auth_hr_client.patch(f'{URL}{obj.id}/', {
            'title': '新标题', 'category': 'NOTICE', 'audience': 'RECRUIT_EXPERT',
            'summary': '新概述', 'body': '新正文', 'pinned': True, 'is_active': False,
        }, format='json')
        assert resp.status_code == 200, resp.content
        obj.refresh_from_db()
        assert obj.title == '新标题'
        assert obj.category == 'NOTICE'
        assert obj.summary == '新概述'
        assert obj.is_active is False
