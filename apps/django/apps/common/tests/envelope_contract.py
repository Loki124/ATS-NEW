"""统一信封契约断言 + 统一契约测试（#35：合并 24 份 test_envelope.py 的重复断言）。

此前每个 app 的 `tests/test_envelope.py` 都各自定义了一遍 `_assert_envelope`，
仅签名略异（有的带 `code=0`、有的 `*, code=0`、integration 版无 code）。
现把契约断言**单源化**到此模块，所有 app 改为 `from ... import assert_envelope`。

契约定义：响应体为 dict，`success is True`，含 `data` 键，`code == 0`。

本模块自包含（`super_user` / `auth_client` fixture 内联），不依赖具体 app 的 conftest，
保证统一契约测试在任意收集路径下都能跑。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.fixtures_common import _create_role_v2, _raw_attach_v2_role


def assert_envelope(body, *, code: int = 0) -> None:
    """统一信封契约: 响应体为 dict, success=True, 含 data 键, code==0。"""
    assert isinstance(body, dict), f'响应非 dict: {body!r}'
    assert body.get('success') is True, f"success 非 True: {body!r}"
    assert 'data' in body, f'缺 data 键: {body!r}'
    assert body.get('code') == code, f"code 非 {code}: {body!r}"


@pytest.fixture
def super_user(db):
    """复刻全局 super_user（V2 兼容：raw SQL 写 id/role_id 规避 V1 NOT NULL）。"""
    from apps.core.models import Department
    from apps.core.models_permission_v2 import RoleV2
    dept, _ = Department.objects.get_or_create(
        id='dept-v2-api',
        defaults={'name': 'V2 API dept', 'code': 'V2_API_DEPT', 'path': '/V2'},
    )
    role = RoleV2.objects.filter(
        system_code='recruit', role_code='SUPER_ADMIN_V2',
    ).first()
    if role is None:
        role = _create_role_v2('SUPER_ADMIN_V2', '超级管理员V2')
    user = get_user_model().objects.create_user(
        username='admin_v2_api',
        password='Test@1234',
        employee_id='EV2API',
        is_staff=True,
        is_superuser=True,
        department=dept,
    )
    _raw_attach_v2_role(user, role)
    return user


@pytest.fixture
def auth_client(super_user):
    """已认证 API client (Bearer JWT, super_user 身份)。"""
    client = APIClient()
    refresh = RefreshToken.for_user(super_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


# ---------------------------------------------------------------------------
# 统一契约测试：扫描各 app 的 list 端点，守住「返回统一信封」契约。
# 注册表只收录「GET list 返回 200 + 信封」的端点；新增端点时在此登记即可。
# 各 app 的 test_envelope.py 仍保留各自细粒度（创建/更新/字段回填）用例。
# ---------------------------------------------------------------------------
ENVELOPE_LIST_ENDPOINTS = [
    # core / 权限域
    '/api/v1/users/',
    '/api/v1/user-roles/',
    '/api/v1/permissions/resources/',
    '/api/v1/permissions/templates/',
    '/api/v1/roles/',
    '/api/v1/management-units/',
    '/api/v1/user-app-data-scopes/',
    # 业务域
    '/api/v1/audit-logs/',
    '/api/v1/applications/',
    '/api/v1/positions/',
    '/api/v1/offers/',
    '/api/v1/onboardings/',
    '/api/v1/invitations/',
    '/api/v1/data-permissions/',
    '/api/v1/dictionary-types/',
    '/api/v1/dictionary-items/',
    '/api/v1/stages/',
    '/api/v1/processes/',
    '/api/v1/process-stage-links/',
    '/api/v1/recruitment-rounds/',
    '/api/v1/analytics/exports/',
    '/api/v1/automation-rules/',
    '/api/v1/automation-rules/logs/',
    '/api/v1/announcements/',
    '/api/v1/resumes/approval-flows/',
    '/api/v1/integrations/',
    # 注: /api/v1/metrics/ 与 /api/v1/library/ 是 DRF 路由根视图
    # (返回子端点 URL 字典, 非列表信封), 不入契约注册表; 其真实 list 端点
    # (metrics/atomic-metrics、library/majors 等) 由各 app test_envelope.py 覆盖.
]


@pytest.mark.django_db
@pytest.mark.parametrize('endpoint', ENVELOPE_LIST_ENDPOINTS)
def test_envelope_list_contract(auth_client, endpoint):
    """每个登记 list 端点都须返回统一信封 {success, data, code}。"""
    resp = auth_client.get(endpoint)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert isinstance(body['data'], list)
