"""pytest 全局共享 fixtures (Phase 1C)

2026-08-03 R7 (寇豆码): 本文件原名 `tests/conftest.py`, 现改为普通 plugin 模块,
由 rootdir 顶层 `apps/django/conftest.py` 用 `pytest_plugins` 全局加载.

  为什么要改名: `testpaths` 从 `tests` 放开到 `tests apps` 后, apps/*/tests/ 需要
  复用这里的 hr_user / super_user / auth_client 等基础 fixture. 但 conftest 只对
  自己所在目录树的**下方**生效, tests/ 与 apps/ 是 sibling. 若在顶层 conftest 写
  `pytest_plugins = ['tests.conftest']`, 同一个文件会被 pytest 同时按 "conftest"
  和 "plugin" 两种身份注册, 抛
  `ValueError: Plugin already registered under a different name`.
  改名为非 conftest 模块后只有 plugin 一种身份, 且对全量测试生效.

T30.175 (V2 cutover follow-up): fixtures 同时支持 V1 (test DB SQLite, V1 migrations)
和 V2 (dev MySQL, V2 cutover applied). 通过探测 roles 表是否有 role_code 列
动态选择路径. 这保证单测在切库前/切库后都能跑.

2026-08-03: 把 _v2_schema_present() 改返 True (测试环境统一走 V2 path) + session 级
fixture 强制 V1 UserRole 写 V2 列. 修 7 个 fail:
- test_demand/test_candidate/test_referral 403 (V2 permission_check 找不到 role_code)
- test_field_acl mask 不到 NONE 规则 (V2 user_role_codes 查不到数据)
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import Department, Role as _V1_Role
from apps.core.models_permission_v2 import RoleV2, UserRoleV2


_FORCE_V2 = True  # 2026-08-03: 强制 V2 path, 跟真实 MySQL 一致


def _v2_schema_present() -> bool:
    """探测 V2 schema 是否就绪. 2026-08-03 改成强制返 True (测试环境统一走 V2 path)."""
    if _FORCE_V2:
        return True
    try:
        with connection.cursor() as c:
            if connection.vendor == 'sqlite':
                c.execute("PRAGMA table_info(roles)")
            else:
                c.execute("DESCRIBE roles")
            cols = {row[1] for row in c.fetchall()}
        return 'role_code' in cols
    except Exception:
        return False


def _ensure_v2_schema_on_sqlite():
    """session 级: 给 sqlite 测试 DB 的 user_roles / roles 表补 V2 列.

    原因: V1 `UserRole.managed=False` + V2 `UserRoleV2.managed=True` 共用 db_table='user_roles',
    但 0002_v2_init 用 SeparateDatabaseAndState 不真建表. V2 业务代码 (permission_check.py
    / role_v2_query.py) 查 user_roles.role_code 会抛 no such column → 403.

    schema 不兼容点 (V1 vs V2):
    - roles.id: VARCHAR(32) (V1) vs BigAuto (V2). SQLite 不能直接改 PK 类型, 我们给 V1 表加 V2 列,
      V1 fixtures 通过 model save() 走 V1 INSERT (依赖 V1 role.id PK 写), role.id 是 nanoid 字符串
      也 OK. 走 V2 path 时 model save() 用 BigAuto, 但底层表 id 是 VARCHAR(32) — 我们要保证 V2
      fixtures 不显式 set id, 走 AUTO. SQLite 的 INTEGER PRIMARY KEY = rowid 整数, 但 V1 表是
      VARCHAR(32) PRIMARY KEY. 所以 V2 fixtures 必须显式给 id.
    - user_roles.role_id (FK) NOT NULL (V1) vs 不存在 (V2). 兼容: V1 fixtures 必填 role_id, V2
      fixtures 走 raw SQL INSERT (不依赖 model, 不触发 NOT NULL).

    这里:
    1. roles 表加 V2 列 (role_code/system_code/role_name/...), V1 PK 不动
    2. user_roles 表加 V2 列 (role_code/system_code/management_unit_ids/...), V1 列保留 NOT NULL
       (V1 fixtures 仍能用)
    3. 提供 _raw_attach_v2_role helper 用 raw SQL 写 V2 path, 绕过 V1 NOT NULL 约束
    """
    if connection.vendor != 'sqlite':
        return  # MySQL: 真实 V2 schema 已 apply, 不动
    with connection.cursor() as c:
        c.execute("PRAGMA table_info(roles)")
        roles_cols = {row[1] for row in c.fetchall()}
        v2_roles_cols = {
            'role_name': 'VARCHAR(64)',
            'role_code': 'VARCHAR(64)',
            'system_code': "VARCHAR(32) DEFAULT 'recruit'",
            'template_code': 'VARCHAR(64)',
            'default_data_scope_type': 'VARCHAR(32)',
            'description': 'VARCHAR(255)',
            'is_system': 'SMALLINT DEFAULT 0',
            'status': 'SMALLINT DEFAULT 1',
            'created_at': 'DATETIME',
            'updated_at': 'DATETIME',
        }
        for col, decl in v2_roles_cols.items():
            if col not in roles_cols:
                c.execute(f"ALTER TABLE roles ADD COLUMN {col} {decl}")

        c.execute("PRAGMA table_info(user_roles)")
        ur_cols = {row[1] for row in c.fetchall()}
        v2_ur_cols = {
            'role_code': 'VARCHAR(64)',
            'system_code': "VARCHAR(32) DEFAULT 'recruit'",
            'management_unit_ids': 'TEXT',
            'valid_from': 'DATE',
            'valid_to': 'DATE',
            'updated_at': 'DATETIME',
        }
        for col, decl in v2_ur_cols.items():
            if col not in ur_cols:
                c.execute(f"ALTER TABLE user_roles ADD COLUMN {col} {decl}")


def _raw_attach_v2_role(user, role):
    """绕过 model 的 raw SQL 写入, 让 V2 fixtures 不被 V1 NOT NULL 约束卡住.

    V2 fixtures 调用此函数 (替代 UserRoleV2.objects.get_or_create):
    - user_role_codes() 查 user_roles.role_code 命中
    - 写一个真实 role_id (V1 FK → roles.id, 我们刚才 raw SQL 写的 V1 PK)
    """
    with connection.cursor() as c:
        c.execute(
            "SELECT id FROM roles WHERE role_code=%s AND system_code='recruit' LIMIT 1",
            [role.role_code],
        )
        row = c.fetchone()
        if not row:
            raise RuntimeError(f'V2 role {role.role_code} not in roles table — call _create_role_v2 first')
        v1_role_pk = row[0]
        c.execute(
            """INSERT INTO user_roles
               (user_id, role_id, role_code, system_code, granted_at)
               VALUES (%s, %s, %s, 'recruit', CURRENT_TIMESTAMP)""",
            [user.pk, v1_role_pk, role.role_code],
        )


@pytest.fixture(autouse=True, scope='session')
def _ensure_v2_schema(django_db_setup, django_db_blocker):
    """session 级 autouse: 测试 DB 初始化完后, 强制补 V2 schema + seed 权限表.

    - 补 V2 列 (role_code / system_code / ...) 到 user_roles + roles
    - seed role_permission 表 (V2 业务 has_perm 查这个, 没 seed 永远 403)
    """
    from django.utils import timezone
    from django.core.management import call_command
    with django_db_blocker.unblock():
        # pytest-django 默认在 test 时 migrate, 但 fixture 可能在 migrate 之前跑.
        # 显式跑一次 migrate 确保所有表都在.
        call_command('migrate', verbosity=0, interactive=False, run_syncdb=True)
        _ensure_v2_schema_on_sqlite()
        # ---- seed role_permission: HR/HRBP/SUPER_ADMIN 都有 recruit:domain:list 权限 ----
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*) FROM role_permission")
            if c.fetchone()[0] == 0:
                # 扫描所有 ViewSet 用了 permission_required = 'recruit:domain:list' 的 resource_code
                from django.apps import apps
                resource_codes = set()
                for app_config in apps.get_app_configs():
                    try:
                        module = __import__(app_config.name + '.views', fromlist=[''])
                        for attr_name in dir(module):
                            cls = getattr(module, attr_name, None)
                            if cls is None or not hasattr(cls, 'permission_required'):
                                continue
                            if isinstance(cls.permission_required, str):
                                resource_codes.add(cls.permission_required)
                            elif isinstance(cls.permission_required, (list, tuple)):
                                resource_codes.update(cls.permission_required)
                    except ImportError:
                        pass
                # 给 HR/HRBP/SUPER_ADMIN 三个角色都授权
                now = timezone.now()
                seeded = 0
                for role_code in ('SUPER_ADMIN', 'HRBP', 'HR'):
                    for rc in resource_codes:
                        c.execute(
                            """INSERT INTO role_permission
                               (role_code, resource_code, system_code, created_at)
                               VALUES (%s, %s, 'recruit', %s)""",
                            [role_code, rc, now],
                        )
                        seeded += 1
                print(f'[conftest] seeded {seeded} role_permission rows for {len(resource_codes)} resources')
            # 注: roles.default_data_scope_type=ALL 在 _create_role_v2 里设, 这里不再 UPDATE
            # (因为 session fixture 跑得比 function fixtures 早, 当时 roles 表还是空的)


@pytest.fixture
def user_model():
    return get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def department(db):
    return Department.objects.create(
        id='dept-test-001',
        name='测试部门',
        code='TEST_DEPT',
        path='/测试部门',
    )


@pytest.fixture
def hr_role(db):
    if _v2_schema_present():
        return _create_role_v2('HR', 'HR')
    return _V1_Role.objects.create(
        id='role-hr-001', code='HR', name='HR', is_active=True,
    )


@pytest.fixture
def hrbp_role(db):
    if _v2_schema_present():
        return _create_role_v2('HRBP', 'HRBP')
    return _V1_Role.objects.create(
        id='role-hrbp-001', code='HRBP', name='HRBP', is_active=True,
    )


@pytest.fixture
def super_admin_role(db):
    if _v2_schema_present():
        return _create_role_v2('SUPER_ADMIN', '超级管理员')
    return _V1_Role.objects.create(
        id='role-super-001', code='SUPER_ADMIN', name='超级管理员', is_active=True,
    )


def _create_role_v2(code: str, name: str):
    """V2 fixtures: 用 raw SQL 写 roles 表, 兼容 V1 VARCHAR(32) PK 约束.

    V1 roles 表 id 是 VARCHAR(32) NOT NULL, V2 RoleV2 是 BigAuto, 在 sqlite 上 model save() 不
    自动给 id (BigAuto 在 sqlite 不通过 INTEGER PRIMARY KEY 推断). 我们手动 INSERT 显式 id.

    2026-08-03: 同时设 default_data_scope_type='ALL', 让 HR/HRBP/SUPER_ADMIN 角色的
    ScopeQuerysetMixin 走 L2 ALL 路径 (绕过 IDOR, list 端点能拿到全部数据).
    """
    from django.utils import timezone
    import uuid
    with connection.cursor() as c:
        c.execute(
            """INSERT INTO roles
               (id, code, name, description, is_builtin, is_active, role_code, role_name,
                system_code, status, default_data_scope_type, created_at, updated_at)
               VALUES (%s, %s, %s, '', 0, 1, %s, %s, 'recruit', 1, 'ALL', %s, %s)""",
            [f'role-{code.lower()}-{uuid.uuid4().hex[:8]}', code, name, code, name,
             timezone.now(), timezone.now()],
        )
    return RoleV2.objects.get(role_code=code, system_code='recruit')


def _attach_role(user, role) -> None:
    """T30.175: V2 → raw SQL 写 user_roles (兼容 V1 表 NOT NULL 约束);
    V1 → user.user_roles. 根据 role 类型自动分支.

    2026-08-03: V2 path 改用 raw SQL (因为 V1 user_roles.role_id NOT NULL, model 走不通)
    """
    if isinstance(role, RoleV2):
        _raw_attach_v2_role(user, role)
    else:
        # V1 path (test DB on SQLite still runs V1 migrations)
        user.user_roles.create(role=role, department=None)


@pytest.fixture
def hr_user(db, department, hr_role):
    user = get_user_model().objects.create_user(
        username='hr_zhang',
        password='Test@1234',
        employee_id='E001',
        department=department,
    )
    _attach_role(user, hr_role)
    return user


@pytest.fixture
def hrbp_user(db, department, hrbp_role):
    user = get_user_model().objects.create_user(
        username='hrbp_li',
        password='Test@1234',
        employee_id='E002',
        department=department,
    )
    _attach_role(user, hrbp_role)
    return user


@pytest.fixture
def super_user(db, department, super_admin_role):
    user = get_user_model().objects.create_user(
        username='admin',
        password='Test@1234',
        employee_id='E000',
        is_staff=True,
        is_superuser=True,
        department=department,
    )
    _attach_role(user, super_admin_role)
    return user


@pytest.fixture
def auth_client(super_user):
    """已认证的 API client"""
    client = APIClient()
    refresh = RefreshToken.for_user(super_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def auth_hr_client(hr_user):
    """HR 身份认证 client"""
    client = APIClient()
    refresh = RefreshToken.for_user(hr_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def auth_hrbp_client(hrbp_user):
    """HRBP 身份认证 client"""
    client = APIClient()
    refresh = RefreshToken.for_user(hrbp_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client
