"""campus app V2 权限整改冒烟测试（Batch 0 任务 #18）。

把 CampusAmbassadorViewSet / CampusSessionViewSet 从裸 IsAuthenticated 切到
V2Permission + 复用 campus_control 资源码（recruit:settings:campus_control:*）。

断言：
- 已登录但无任何角色的用户访问 → 403（不再裸放行）；
- 持有 campus_control:list 码的用户（super_user / HR，测试库已 seed 全部码）→ 200。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


def _client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.mark.django_db
class TestCampusRecruitV2Wiring:
    def test_ambassadors_list_requires_v2_code(self, auth_client):
        resp = auth_client.get('/api/v1/campus-recruit/ambassadors/')
        assert resp.status_code == 200

    def test_sessions_list_requires_v2_code(self, auth_client):
        resp = auth_client.get('/api/v1/campus-recruit/sessions/')
        assert resp.status_code == 200

    def test_plain_user_denied(self, db):
        User = get_user_model()
        plain = User.objects.create_user(username='plain_campus', password='x', employee_id='PC')
        client = _client_for(plain)
        resp = client.get('/api/v1/campus-recruit/ambassadors/')
        assert resp.status_code == 403

    def test_hr_user_allowed(self, auth_hr_client):
        resp = auth_hr_client.get('/api/v1/campus-recruit/ambassadors/')
        assert resp.status_code == 200
