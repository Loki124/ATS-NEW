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

    # ===== 模块配置：工作台展示开关 =====
    def test_config_get_default_true(self, auth_hr_client):
        """GET 配置默认 show_on_workbench=True，且单例行被保证存在。"""
        resp = auth_hr_client.get(CONFIG_URL)
        assert resp.status_code == 200
        # 渲染器输出为驼峰 showOnWorkbench
        assert resp.json()['data']['showOnWorkbench'] is True
        assert AnnouncementConfig.objects.filter(pk=1).exists()

    def test_config_put_requires_hr(self, api_client):
        """非 HR 修改配置 → 403。"""
        from django.contrib.auth import get_user_model
        plain = get_user_model().objects.create_user(username='plain2', password='x')
        api_client.force_authenticate(user=plain)
        resp = api_client.put(CONFIG_URL, {'show_on_workbench': False}, format='json')
        assert resp.status_code == 403

    def test_config_put_updates_and_persists(self, auth_hr_client):
        """HR 关闭工作台展示，GET 与 DB 均反映。"""
        put = auth_hr_client.put(CONFIG_URL, {'show_on_workbench': False}, format='json')
        assert put.status_code == 200
        assert put.json()['data']['showOnWorkbench'] is False
        # 再次读取保持关闭
        assert auth_hr_client.get(CONFIG_URL).json()['data']['showOnWorkbench'] is False
        cfg = AnnouncementConfig.objects.get(pk=1)
        assert cfg.show_on_workbench is False
