"""方案 A(2026-09-15): UserAppDataScope ViewSet 运行时测试 (per-app 数据范围).

直接打真实 HTTP 到 DRF 客户端(等价运行中服务端), 验证 upsert + 按 (user_id,app_code) 过滤.
不依赖 shell is_valid 假绿 —— APIClient 走完整 DRF parser/renderer 链路.
"""
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_user_app_data_scope_upsert_and_filter():
    User = get_user_model()
    admin = User.objects.create_user(username='uadsadmin', password='x', is_superuser=True)
    client = APIClient()
    client.force_authenticate(admin)

    # 1) create
    r = client.post('/api/v1/user-app-data-scopes/', {
        'userId': 1, 'roleCode': 'R_X', 'appCode': 'campus',
        'systemCode': 'recruit', 'managementUnitIds': [1, 2],
    }, format='json')
    assert r.status_code == 201, r.content
    d = r.json()['data']
    first_id = d['id']
    assert d['managementUnitIds'] == [1, 2]
    assert d['appCode'] == 'campus'

    # 2) upsert 同键 -> id 不变, 内容更新
    r2 = client.post('/api/v1/user-app-data-scopes/', {
        'userId': 1, 'roleCode': 'R_X', 'appCode': 'campus',
        'systemCode': 'recruit', 'managementUnitIds': [3],
    }, format='json')
    assert r2.status_code == 201, r2.content
    d2 = r2.json()['data']
    assert d2['id'] == first_id
    assert d2['managementUnitIds'] == [3]

    # 3) 不同 app_code -> 独立一行
    r3 = client.post('/api/v1/user-app-data-scopes/', {
        'userId': 1, 'roleCode': 'R_X', 'appCode': 'social',
        'systemCode': 'recruit', 'managementUnitIds': [9],
    }, format='json')
    assert r3.status_code == 201, r3.content

    # 4) filter by user_id + app_code
    rf = client.get('/api/v1/user-app-data-scopes/?user_id=1&app_code=campus')
    assert rf.status_code == 200
    rows = rf.json()['data']
    assert len(rows) == 1
    assert rows[0]['appCode'] == 'campus'
    assert rows[0]['managementUnitIds'] == [3]

    # 5) 缺必填 -> 400
    r4 = client.post('/api/v1/user-app-data-scopes/', {'userId': 1}, format='json')
    assert r4.status_code == 400, r4.content
