"""campus_assessment 测试公共装置。

⚠️ 为什么共享装置放在 `tests/__init__.py` 而不是 `tests/conftest.py`：
   契约（§2.4）给本 app 的测试交付清单是 `tests/__init__.py` + 4 个测试文件，
   共享装置放进包初始化文件即可**不新增交付文件**；pytest 以
   `apps.campus_assessment.tests` 包导入测试文件，`from apps.campus_assessment.tests import ...`
   可直接取用。

装置要点（照抄 apps/campus_control/tests/test_campus_isolation.py 的做法）：
- 角色 / 授权用 `INSERT IGNORE` 幂等写入（测试库 `--reuse-db` 下 session 级
  fixture 不会持久化，用例会话自行授权才能真实通过 V2Permission 守卫）；
- 资源码用 ORM `get_or_create` 登记 —— V2Permission 对**派生写码**是 fail-closed：
  码未登记在 `permission_resources` → 写操作一律拒绝（fail-closed 是有意的，
  见 apps/core/permissions_v2.py）；
- 鉴权走真实 JWT（APIClient + RefreshToken），不打桩。
"""
import uuid

from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models_permission_v2 import PermissionResource, RolePermissionV2

USER = get_user_model()

#: 本 app 的接口前缀（契约 §2.2）
BASE = '/api/v1/campus-assessment'

#: 本 app 用到的资源码（契约 §1.2；与父会话 core/0051 登记的码一致）
RESOURCE_CODES = (
    'recruit:campus:assessment:list',
    'recruit:campus:assessment:create',
    'recruit:campus:assessment:edit',
    'recruit:campus:assessment:delete',
    'recruit:campus:attendance:list',
    'recruit:campus:attendance:create',
    'recruit:campus:attendance:edit',
    'recruit:campus:monthly_report:list',
    'recruit:campus:monthly_report:create',
    'recruit:campus:monthly_report:edit',
    'recruit:campus:monthly_report:evaluate',
    'recruit:campus:feedback:list',
    'recruit:campus:feedback:create',
    'recruit:campus:feedback:edit',
    'recruit:campus:feedback:delete',
)


def uid():
    """短唯一串（避免跨用例撞名 —— 仓库 pytest-randomly 的既有教训）。"""
    return uuid.uuid4().hex[:8]


def ensure_role(role_code):
    """幂等创建 V2 角色（INSERT IGNORE）。"""
    now = timezone.now()
    with connection.cursor() as c:
        c.execute(
            """INSERT IGNORE INTO roles
               (system_code, role_code, role_name, description, is_system,
                status, default_data_scope_type, created_at, updated_at)
               VALUES ('recruit', %s, %s, '', 0, 1, 'ALL', %s, %s)""",
            [role_code, role_code, now, now],
        )


def attach_role(user, role_code):
    """给用户挂 V2 角色（INSERT IGNORE）。"""
    ensure_role(role_code)
    now = timezone.now()
    with connection.cursor() as c:
        c.execute(
            """INSERT IGNORE INTO user_roles
               (user_id, role_code, system_code, granted_by_id, granted_at, updated_at)
               VALUES (%s, %s, 'recruit', %s, %s, %s)""",
            [user.pk, role_code, user.pk, now, now],
        )


def grant(role_code, *resource_codes):
    """给角色授权资源码（幂等）。"""
    for code in resource_codes:
        RolePermissionV2.objects.get_or_create(
            role_code=role_code,
            resource_code=code,
            defaults={'system_code': 'recruit'},
        )


def ensure_resource(*resource_codes):
    """登记资源码到 `permission_resources`（幂等）。

    为什么必须登记：V2Permission 对派生写码是 **fail-closed** —— 码不在资源表里
    就拒绝写操作（不是回退到读码）。父会话 core/0051 会在存量库补齐，
    本函数保证用例自包含、不依赖迁移时序。
    """
    for code in resource_codes:
        PermissionResource.objects.get_or_create(
            resource_code=code,
            defaults={
                'system_code': 'recruit',
                'resource_name': code,
                'resource_type': 'BUTTON',
                'status': 1,
            },
        )


def make_user(username=None, role_code=None, resource_codes=None, is_superuser=False):
    """造一个用户；给了 role_code 就挂角色并授权资源码。

    `resource_codes` 省略时授权本 app 用到的**全部**码（`RESOURCE_CODES`）——
    否则带角色的用户会因为「没授权任何码」在 V2Permission 处 403，
    测的就不是业务逻辑而是授权配置了。
    """
    username = username or f'u_{uid()}'
    user = USER.objects.create_user(
        username=username,
        password='Test@1234',
        employee_id=f'E{uid().upper()}',
        is_superuser=is_superuser,
    )
    if role_code:
        attach_role(user, role_code)
        ensure_resource(*RESOURCE_CODES)
        grant(role_code, *(resource_codes if resource_codes is not None else RESOURCE_CODES))
    return user


def admin_user():
    """超管：可见全部人员 + 绕过资源码守卫（用于排名/统计类用例）。"""
    return make_user(is_superuser=True)


def client_for(user):
    """真实 JWT 客户端。"""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


def make_classroom(code=None, name=None, head_teacher=None):
    """造班级（campus_rotation.ClassRoom）。"""
    from apps.campus_rotation.models import ClassRoom

    code = code or f'CL{uid()[:3]}'
    name = name or f'班级{uid()[:3]}'
    return ClassRoom.objects.create(code=code, name=name, head_teacher=head_teacher)


def make_person(name='张三', head_teacher=None, mentor=None, class_room=None,
                status='在职', user=None):
    """造校招生档案（campus_control.Person）。"""
    from apps.campus_control.models import Person

    return Person.objects.create(
        code=f'C{uid()}', name=name, bu='能电BG', school='985', sex='男',
        major='工学', month='1月', status=status,
        head_teacher=head_teacher, mentor=mentor, class_room=class_room,
        user_id=user.pk if user else None,
    )


def list_rows(payload):
    """从列表响应里取出数据行（兼容信封 + 分页两种形态）。"""
    data = payload.get('data')
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get('results') or []
    return []
