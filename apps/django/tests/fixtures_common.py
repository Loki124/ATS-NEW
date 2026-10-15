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

from apps.core.models import Department
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
    - T01.1 前 (V1 hybrid schema): 写 user_id + role_id (V1 FK) + role_code (V2)
    - T01.1 后 (V2 fresh schema): 写 user_id + role_code + system_code + granted_by_id + granted_at
      (无 role_id 列)

    检测: 看 user_roles 是否有 role_id 列.
    """
    from django.utils import timezone
    with connection.cursor() as c:
        c.execute(
            "SELECT id FROM roles WHERE role_code=%s AND system_code='recruit' LIMIT 1",
            [role.role_code],
        )
        row = c.fetchone()
        if not row:
            raise RuntimeError(f'V2 role {role.role_code} not in roles table — call _create_role_v2 first')
        role_pk = row[0]

        # 探测 user_roles 是否有 role_id 列 (V1 hybrid schema 才有).
        # MySQL 统一走 V2 fresh schema, 无 role_id 列; 仅 SQLite escape-hatch 路径需 PRAGMA 探测.
        has_role_id = False
        if connection.vendor == 'sqlite':
            c.execute("PRAGMA table_info(user_roles)")
            cols = {row[1] for row in c.fetchall()}
            has_role_id = 'role_id' in cols

        if has_role_id:
            # V1 hybrid schema (T01.1 前): 写 V1 FK + V2 列
            c.execute(
                """INSERT INTO user_roles
                   (user_id, role_id, role_code, system_code, granted_at)
                   VALUES (%s, %s, %s, 'recruit', CURRENT_TIMESTAMP)""",
                [user.pk, role_pk, role.role_code],
            )
        else:
            # V2 fresh schema (T01.1 后): 只写 V2 列
            now = timezone.now()
            c.execute(
                """INSERT INTO user_roles
                   (user_id, role_code, system_code, granted_by_id, granted_at, updated_at)
                   VALUES (%s, %s, 'recruit', %s, %s, %s)""",
                [user.pk, role.role_code, user.pk, now, now],
            )


# 缓存所有 ViewSet 声明的 resource_code 集合 (进程内计算一次即可, 重 seed 时直接复用,
# 避免每次空表都重新 import 全量 .views 模块, 见 pytest_runtest_setup 的惰性重 seed).
_ROLE_PERMISSION_RESOURCE_CODES = None


def _collect_resource_codes():
    """扫描全部 apps 的 .views 模块, 收集所有 ViewSet 声明的 permission_required
    / permission_required_map 资源码 (含 V2Permission 按 action 派生的 :create/:edit/:delete).

    结果进程内缓存, 因为 app 注册表在测试进程内不变.
    """
    global _ROLE_PERMISSION_RESOURCE_CODES
    if _ROLE_PERMISSION_RESOURCE_CODES is not None:
        return _ROLE_PERMISSION_RESOURCE_CODES
    from django.apps import apps
    resource_codes = set()
    for app_config in apps.get_app_configs():
        try:
            module = __import__(app_config.name + '.views', fromlist=[''])
        except ImportError:
            continue
        for attr_name in dir(module):
            cls = getattr(module, attr_name, None)
            if cls is None:
                continue
            # 只声明 permission_required_map 的视图 (写操作显式授权、读操作留空) 也必须采到.
            declared = getattr(cls, 'permission_required', None)
            mapping = getattr(cls, 'permission_required_map', None)
            if declared is None and not mapping:
                continue
            if isinstance(declared, str):
                resource_codes.add(declared)
                # V2Permission 按 action 派生写权限码 (:create/:edit/:delete).
                # 测试库里 PermissionResource 未 seed, 派生码若存在就会要求 HR 持有,
                # 故此处一并授予, 让 fixture 语义等价于「该资源的所有操作都放行」.
                base = declared.rsplit(':', 1)[0]
                resource_codes.update(
                    f'{base}:{s}' for s in ('create', 'edit', 'delete')
                )
            elif isinstance(declared, (list, tuple)):
                resource_codes.update(declared)
            # 显式 action 覆盖表里的码也必须授予 (值支持 str 或 list/tuple).
            if isinstance(mapping, dict):
                for v in mapping.values():
                    if isinstance(v, (list, tuple)):
                        resource_codes.update(v)
                    else:
                        resource_codes.add(v)
    _ROLE_PERMISSION_RESOURCE_CODES = resource_codes
    return resource_codes


def _seed_role_permissions(connection):
    """把 HR / HRBP / SUPER_ADMIN 三个角色对所有 resource_code 的授权写入 role_permission.

    调用方需保证调用前 role_permission 为空 (避免重复行); 这里不重复检查, 由调用处
    `COUNT(*) == 0` 守卫.
    """
    from django.utils import timezone
    resource_codes = _collect_resource_codes()
    now = timezone.now()
    seeded = 0
    with connection.cursor() as c:
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


def _seed_action_dictionary():
    """把动作字典种子幂等灌入 ``data_permission_actions`` / ``..._presets``。

    2026-10-14: 修复跨 app 顺序污染的第二载体。

    ``serialized_rollback`` 用例会把 DB 回滚到 ``django_db_setup`` 时的快照, 而
    ``action_map.sync_seed()`` 是**迁移 0006** 灌的 —— 快照拍在 seed 之前, 故回滚后
    字典表为空。此后 ``action_registry`` 读到空字典 → ``validate_write_actions``
    报「未知动作 key: edit」、``is_writable(action='edit')` 全 False。

    表现为「同一份代码连跑几轮, 失败数在 0 / 6 / 26 / 32 之间跳」—— 取决于
    ``pytest-randomly`` 把那 3 个 rollback 用例排在了前面还是后面, 故一直误判为
    环境问题。根治点就在这里: 与 ``role_permission`` 同构, 惰性补种子。

    用 ``sync_seed()`` 而非手写 INSERT —— 它是 ``action_registry`` 自己的兜底源,
    两者保证同一份语义, 不会漂移。
    """
    try:
        from apps.data_permission.action_map import sync_seed

        sync_seed()
        # 字典刚被改动 -> 必须失效 TTL 缓存, 否则读到的还是回滚前的旧值
        from apps.data_permission.action_registry import invalidate_cache

        invalidate_cache()
    except Exception:  # noqa: BLE001 — 无 DB 连接的纯单测跳过, 不影响
        pass


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup(item):
    """惰性重 seed role_permission **与动作字典种子**, 修复 test_migration_0005 等使用
    django_db_serialized_rollback 的用例把会话级 seed 清空、导致后续依赖权限的用例
    403 / 动作字典为空 的问题.

    机制: TransactionTestCase 的 serialized_rollback 在 _fixture_setup (setup 阶段)
    用 loaddata 把 DB 重载到 django_db_setup 时拍的快照 (此时 _ensure_v2_schema 尚未
    seed, role_permission 为空); 非 transaction 用例靠事务回滚不会清空它, 但 migration
    类用例会在 setup 与 teardown 两处把它清零 (loaddata / flush).
    本 hook 用 trylast 保证在默认 pytest_runtest_setup 之后运行 —— 默认 hook 会调用
    _setupstate.setup → _django_db_helper._pre_setup → loaddata 清零, 本 hook 在其后
    才执行, 因此每个测试体执行前 role_permission 与动作字典一定已就绪.

    仅在为空时才写入 role_permission (一次 COUNT 查询); 动作字典走 ``sync_seed()``
    幂等补齐 (它内部按 key 存在与否决定建/更新, 开销可忽略).
    """
    from django.db import connection as _conn
    try:
        with _conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM role_permission")
            if c.fetchone()[0] == 0:
                _seed_role_permissions(_conn)
    except Exception:
        # 无 DB 连接的纯单测直接跳过, 不影响.
        pass
    _seed_action_dictionary()


@pytest.fixture(autouse=True, scope='session')
def _ensure_v2_schema(django_db_setup, django_db_blocker):
    """session 级 autouse: 测试 DB 初始化完后, 强制补 V2 schema + seed 权限表.

    - 补 V2 列 (role_code / system_code / ...) 到 user_roles + roles (兼容 V1 表)
    - seed role_permission 表 (V2 业务 has_perm 查这个, 没 seed 永远 403)

    2026-08-03 T01.1 (寇豆码): 移除 `call_command('migrate', run_syncdb=True)` —
    pytest-django --create-db 已经跑过 migrate, 重复调用会触发 SQLite FK check
    报错 (NotSupportedError). 同时 T01.1 把 0004_v2_apply_schema 加进迁移图,
    pytest-django 自然会 apply, 不需要这里手动 migrate.
    """
    with django_db_blocker.unblock():
        _ensure_v2_schema_on_sqlite()
        # 2026-08-03 T01.1 (寇豆码): 不再在 session 起始 seed permission_resources /
        # permission_templates (那会破坏 test_bootstrap 测试 — 它假设空 DB).
        # test_sync_resources_t29 改由 test_sync_resources_empty_array_clears 显式
        # call_command('seed_v2_init') 提供 seed, 这条用例仍能跑通; 其他两条
        # (test_sync_resources_persists_codes / test_sync_resources_rejects_invalid_codes)
        # 暂时仍依赖 QUARANTINE 隔离 (RT-2 验收将由 T01.2/T05 解决).
        # ---- seed role_permission: HR/HRBP/SUPER_ADMIN 都有 recruit:domain:list 权限 ----
        # 复用 _seed_role_permissions (仅在为空时写入); 空表后的惰性重 seed 由
        # pytest_runtest_setup hook 负责 (应对 serialized_rollback 回滚).
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*) FROM role_permission")
            if c.fetchone()[0] == 0:
                _seed_role_permissions(connection)
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
    pytest.skip('V1 path disabled — Role V1 shadow model removed in T01.1')


@pytest.fixture
def hrbp_role(db):
    if _v2_schema_present():
        return _create_role_v2('HRBP', 'HRBP')
    pytest.skip('V1 path disabled — Role V1 shadow model removed in T01.1')


@pytest.fixture
def super_admin_role(db):
    if _v2_schema_present():
        return _create_role_v2('SUPER_ADMIN', '超级管理员')
    pytest.skip('V1 path disabled — Role V1 shadow model removed in T01.1')


def _create_role_v2(code: str, name: str):
    """V2 fixtures: 用 raw SQL 写 roles 表, V2 schema (T01.1 后真表).

    T01.1 前 (V1 path): roles 表是 V1 schema (id VARCHAR(32) + code/name/is_builtin/is_active
    + role_code/role_name/system_code 同时存在, 由 conftest session fixture 临时 ALTER
    ADD COLUMN 补 V2 列). 写时既要写 V1 列又要写 V2 列.

    T01.1 后 (V2 path, fresh DB): roles 表是 V2 schema (id BigAuto + system_code/role_code/
    role_name 等, 无 V1 列). 用 BigAuto 自动 PK, 只需写 V2 列.

    检测方法: 看 `code` 列是否存在. V1 有, V2 无.
    """
    from django.utils import timezone
    import uuid
    now = timezone.now()
    with connection.cursor() as c:
        # 探测 roles 是否有 code 列 (V1 hybrid schema 才有).
        # MySQL 统一走 V2 fresh schema, 无 code 列; 仅 SQLite escape-hatch 路径需 PRAGMA 探测.
        has_code_col = False
        if connection.vendor == 'sqlite':
            c.execute('PRAGMA table_info(roles)')
            cols = {row[1] for row in c.fetchall()}
            has_code_col = 'code' in cols

        if has_code_col:
            # V1 fallback (历史代码路径): 同时写 V1 + V2 列
            c.execute(
                """INSERT INTO roles
                   (id, code, name, description, is_builtin, is_active, role_code, role_name,
                    system_code, status, default_data_scope_type, created_at, updated_at)
                   VALUES (%s, %s, %s, '', 0, 1, %s, %s, 'recruit', 1, 'ALL', %s, %s)""",
                [f'role-{code.lower()}-{uuid.uuid4().hex[:8]}', code, name, code, name,
                 now, now],
            )
        else:
            # V2 fresh schema (T01.1 后): 只写 V2 列
            c.execute(
                """INSERT INTO roles
                   (system_code, role_code, role_name, description,
                    is_system, status, default_data_scope_type, created_at, updated_at)
                   VALUES ('recruit', %s, %s, '', 0, 1, 'ALL', %s, %s)""",
                [code, name, now, now],
            )
    return RoleV2.objects.get(role_code=code, system_code='recruit')


def attach_super_admin(user):
    """给测试用户挂 SUPER_ADMIN 角色 (走 is_super_admin bypass)。

    背景 (2026-10-11 G2): 端点从裸 IsAuthenticated / 角色白名单切到 V2Permission 后,
    「已登录但没有任何角色」的测试用户会 403。这类用例测的是业务逻辑而非权限,
    统一用本 helper 给足权限, 避免逐个用例去补 role_permission 行
    (测试库里 PermissionResource 未 seed, 按码授权反而无从枚举)。
    """
    role = _create_role_v2('SUPER_ADMIN', '超级管理员')
    _attach_role(user, role)
    return user


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
