"""校招专属功能(campus app)集成测试 (Phase 4).

硬证据: 证明校园大使 / 宣讲会 模型经 ScopeQuerysetMixin 自动 recruit_type 硬分区,
写侧由请求上下文权威注入 recruit_type='campus' + 审计字段, 且社招上下文不可见;
模块配置端点 GET/PUT round-trip 正常.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from apps.campus.models import CampusAmbassador, CampusSession
from apps.campus.serializers import CampusAmbassadorSerializer, CampusSessionSerializer
from apps.campus.views import CampusAmbassadorViewSet, CampusModuleConfigView, CampusSessionViewSet


def _view(ViewSet, rt, user):
    """构造一个带 request 上下文的 ViewSet 实例（不走 dispatch，直接测 mixin 行为）。"""
    v = ViewSet()
    v.request = type('Req', (), {'user': user, 'recruit_type': rt})()
    v.args = ()
    v.kwargs = {}
    return v


@pytest.mark.django_db
def test_ambassador_write_injects_campus_and_audit():
    U = get_user_model()
    user = U.objects.create_superuser('campus_a', 'Campus123!')
    v = _view(CampusAmbassadorViewSet, 'campus', user)
    s = CampusAmbassadorSerializer(data={'school': 'SJTU', 'name': '张', 'status': 'active', 'region': '华东'})
    s.is_valid(raise_exception=True)
    v.perform_create(s)
    inst = s.instance
    assert inst.recruit_type == 'campus'
    assert inst.created_by_id == user.id


@pytest.mark.django_db
def test_isolation_social_cannot_see_campus():
    U = get_user_model()
    user = U.objects.create_superuser('campus_b', 'Campus123!')
    CampusAmbassador.objects.create(school='S', name='N', status='active', recruit_type='campus', created_by=user)
    assert _view(CampusAmbassadorViewSet, 'campus', user).get_queryset().count() == 1
    assert _view(CampusAmbassadorViewSet, 'social', user).get_queryset().count() == 0


@pytest.mark.django_db
def test_session_write_injects_campus():
    U = get_user_model()
    user = U.objects.create_superuser('campus_c', 'Campus123!')
    v = _view(CampusSessionViewSet, 'campus', user)
    s = CampusSessionSerializer(data={'title': '宣讲', 'session_type': 'offline', 'status': 'planned'})
    s.is_valid(raise_exception=True)
    v.perform_create(s)
    assert s.instance.recruit_type == 'campus'


@pytest.mark.django_db
def test_config_endpoint_roundtrip():
    U = get_user_model()
    user = U.objects.create_superuser('campus_d', 'Campus123!')
    with override_settings(ALLOWED_HOSTS=['*']):  # APIClient 用 testserver host
        client = APIClient()
        client.force_authenticate(user=user)
        r = client.get('/api/v1/campus-recruit/ambassadors/config/')
        assert r.status_code == 200
        assert r.json()['data'] == {}
        r = client.put('/api/v1/campus-recruit/ambassadors/config/', {'enabled': True}, format='json')
        assert r.status_code == 200
        assert r.json()['data']['enabled'] is True
        r = client.get('/api/v1/campus-recruit/ambassadors/config/')
        assert r.json()['data']['enabled'] is True
