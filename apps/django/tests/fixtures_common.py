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

T30.175 (V2 cutover follow-up): fixtures 仅支持 V2 path（V1 / SQLite 历史分支已随「开发/测试禁用 SQLite」移除，测试库统一为 MySQL）。

2026-08-03: 把 _v2_schema_present() 改返 True (测试环境统一走 V2 path) + session 级
fixture 强制 V1 UserRole 写 V2 列. 修 7 个 fail:
- test_demand/test_candidate/test_referral 403 (V2 permission_check 找不到 role_code)
- test_field_acl mask 不到 NONE 规则 (V2 user_role_codes 查不到数据)
"""
import time

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import Department
from apps.core.models_permission_v2 import RoleV2, UserRoleV2

_FORCE_V2 = True  # 2026-08-03: 强制 V2 path, 跟真实 MySQL 一致


# ---------------------------------------------------------------------------
# 补种可靠性（2026-10-21 整跑 flaky 根因治理）
#
# 背景：`_repair_committed_seeds` 原来用 `except Exception: pass` 吞掉一切异常，
#   其中包括 MySQL 1213 死锁 / 1205 锁等待超时这类**瞬时**错误
#   → 补种静默失效 → 种子没补回来 → 后续用例集体 403 / DoesNotExist。
#   实测表现为：同一份代码整跑，结果在 0 failed 与 8~18 failed 之间乱跳，
#   且**失败集合逐轮不同**（403 权限失败 ↔ MySQL 1213 死锁之间游走）。
#
# 下面三个原语把「吞异常」换成「收窄异常集 + 退避重试 + 失败可见」：
# ---------------------------------------------------------------------------

_REPAIR_MAX_ATTEMPTS = 3
_REPAIR_BACKOFF_SECONDS = 0.2

# 模块导入时（pytest 还没建立测试库）的库名。pytest-django 建库后会把
# settings.DATABASES['default']['NAME'] 换成测试库名（test_<NAME>），
# 于是「当前库名 != _BASE_DB_NAME」等价于「当前连的是测试库」。
_BASE_DB_NAME = settings.DATABASES['default']['NAME']

# 补种过程中的失败记录（label → 异常摘要）。非空说明**有种子没补回来**，
# 后续用例的 403 很可能是它的下游后果 —— 排查时先看这里。
_SEED_REPAIR_FAILURES: list[dict] = []


def in_test_database() -> bool:
    """当前默认连接是否已指向**测试库**。

    🔴 为什么必须判断：``pytest_runtest_setup``(tryfirst) 跑在 ``item.setup()`` **之前**，
    而 pytest-django 是在 ``django_db_setup``（session 级 fixture）里才把库名切成测试库
    → **第一个需要 DB 的用例之前，hook 里的补种连的是开发库**。

    实测后果（2026-10-21）：补种往开发库 ``ats_test`` 写了 552 行 role_permission，
    同时因为开发库的迁移只到 core.0040（没有 ``permission_resources.sub_module`` 列）
    → 补种 INSERT 报 ``(1054, Unknown column ...)`` → 异常被静默吞掉 →
    **测试库的种子其实一次都没被补回来** → 后续用例批量 403（整跑 flaky 的主因之一）。
    """
    from django.db import connection as _conn

    return _conn.settings_dict['NAME'] != _BASE_DB_NAME


def seed_repair_failures() -> list[dict]:
    """返回本次 pytest 会话里「补种失败」的记录（空列表 = 全部补种成功）。"""
    return list(_SEED_REPAIR_FAILURES)


def _is_transient_db_error(exc: BaseException) -> bool:
    """是否「瞬时」的数据库错误（可重试）。

    瞬时：MySQL 1213 死锁 / 1205 锁等待超时 / 2006 连接断开 / 2013 丢连接
          → ``django.db.utils.OperationalError`` / ``InterfaceError``。
    非瞬时：IntegrityError（唯一约束冲突，重复执行无意义）、ProgrammingError（SQL 写错）、
            DataError（脏数据）→ **重试没有意义**，重试只是浪费时间并掩盖真因。
    """
    from django.db.utils import InterfaceError, OperationalError

    return isinstance(exc, (OperationalError, InterfaceError))


def _is_no_db_context(exc: BaseException) -> bool:
    """是否「本来就不该查库」的语境（不是失败）。

    两种：
      ① pytest-django 的 DB 阻断（``RuntimeError: Database access not allowed``）
         —— 无 DB 的纯单测；
      ② ``django.test.testcases.DatabaseOperationForbidden``（**继承 AssertionError**）
         —— ``SimpleTestCase`` 子类禁止查库。

    这两种都**不是**补种失败，只是「这个用例用不着补种」→ 静默跳过。
    （旧实现用 ``except Exception: return True`` 兜住它们；收窄异常集时必须显式保留，
    否则每次跑整跑都会刷出一堆假告警。）
    """
    from django.test.testcases import DatabaseOperationForbidden

    return isinstance(exc, (RuntimeError, DatabaseOperationForbidden))


def _record_repair_failure(label: str, exc: BaseException) -> None:
    """记录一次补种失败 —— 静默失效是本次治理要消灭的行为。"""
    summary = f'{type(exc).__name__}: {exc}'
    _SEED_REPAIR_FAILURES.append({'label': label, 'error': summary})
    # 用 warning 而非 print：pytest 会把它归到「本次运行的告警」里，不会被淹没
    import warnings

    warnings.warn(
        f'[seed-repair] 补种失败：{label} → {summary}',
        RuntimeWarning,
        stacklevel=2,
    )


def _run_with_retry(fn, label: str, *, max_attempts: int = _REPAIR_MAX_ATTEMPTS):
    """执行补种动作；瞬时数据库错误退避重试，仍失败则**记录并返回 None**。

    返回 ``fn()`` 的结果；失败时返回 None（调用方按「没补上」处理）。
    """
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — 下面按是否瞬时分别处理
            if _is_no_db_context(exc):
                return None  # 本来就不该查库 → 不算失败
            last_exc = exc
            if not _is_transient_db_error(exc):
                break
            if attempt < max_attempts:
                time.sleep(_REPAIR_BACKOFF_SECONDS * attempt)
    if last_exc is not None:
        _record_repair_failure(label, last_exc)
    return None


def _v2_schema_present() -> bool:
    """V2 schema 在测试环境始终就绪（V1 / SQLite 分支已移除，测试库统一 MySQL + V2 fresh schema）。"""
    return True


def _ensure_v2_schema_compat():
    """session 级占位: V2 schema 由迁移 0004_v2_apply_schema 真建，测试库统一 MySQL，无需运行时补列。

    旧实现在 SQLite 测试库上用 ALTER TABLE 补 V2 列（V1 hybrid schema 兼容）；
    SQLite 已禁用后该分支为死代码，保留为 no-op 仅作 session fixture 占位。
    """
    return


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

        # 测试库统一 V2 fresh schema（MySQL），无 role_id 列，只写 V2 列
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
        except ImportError as e:
            # 2026-10-21 卡 B5：原来这里**静默** continue —— 该 app 声明的所有权限码
            # 就此从 role_permission 种子里消失 → 用到这些码的用例整片 403
            # （实测 campus_rotation 的 26 条码整族缺失，apps/campus_rotation/tests/
            # test_views.py::TestV2PermissionWiring::test_hr_user_allowed 判红）。
            # 改为**记录原因**再跳过：静默吞掉是这类「权限族整族消失」的根因。
            print(f'[conftest] 跳过 {app_config.name}.views 的权限码采集: {e!r}')
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

    2026-10-21 卡 B5：改为 **幂等 upsert**（``ON DUPLICATE KEY UPDATE``）。
    原来用裸 INSERT：只要表里已有**任意一行**与待插行撞 (role_code, resource_code)
    唯一约束 ``uk_role_resource``，整批 INSERT 就在那一行**中断** —— 之前插进去的留下、
    后面的全丢（静默半截种子）。
    实测：迁移 core.0034 会在 migrate 阶段写入 10 行（SUPER_ADMIN / ADMIN × 5 条动态
    策略码），与本函数要插的行重叠 → HR / HRBP 的 500+ 条授权**一条都没进库**
    → 所有非超管用例 403（实测 apps/campus_rotation/tests/test_views.py::
    TestV2PermissionWiring::test_hr_user_allowed 判红）。
    幂等 upsert 后：重复调用安全、撞唯一约束的行被就地更新而非中断整批。
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
                       VALUES (%s, %s, 'recruit', %s)
                       ON DUPLICATE KEY UPDATE system_code = VALUES(system_code)""",
                    [role_code, rc, now],
                )
                seeded += 1
    print(f'[conftest] seeded {seeded} role_permission rows for {len(resource_codes)} resources')


def _seed_permission_resources():
    """幂等补齐 ``permission_resources``（资源码注册表）—— 真源 = ``seed_v2_init.RESOURCES``。

    2026-10-21 卡 B5 新增。

    为什么必须补：``apps/core/permissions_v2.py`` 的 ``_derive()`` 自卡 A1 起改为
    **fail-closed** —— 派生写码（``:create`` / ``:edit`` / ``:delete``）未在
    ``permission_resources`` 注册时**直接拒绝该写操作**（旧行为是回退到读码，
    等于「持 :list 的账号可写」，是 P0 越权面）。

    而测试环境**从不 seed permission_resources**（见本文件上方 2026-08-03 的说明：
    「不再在 session 起始 seed permission_resources / permission_templates，
    那会破坏 test_bootstrap 测试 — 它假设空 DB」）。于是注册表为空 →
    所有派生写码都被判为「真缺失」→ **非超管账号的写操作一律 403**
    （实测整跑 26 处 ``assert 403 == 200`` / ``403 == 400``）。

    本函数只写 ``permission_resources``，**不写** templates / tenant_config /
    角色 / 管理员用户 —— 那几张表由 ``seed_v2_init`` 命令负责，且有测试
    （``test_bootstrap_missing_template_raises``）明确依赖「模板为空」这一前提。

    语义与 ``seed_v2_init.Command.handle`` 的主循环**逐条对齐**（同真源、同字段、
    同后置处理），避免出现「测试环境与生产环境注册表不一致」的第二个真相源。

    性能：用一条 ``executemany`` 的 ``INSERT ... ON DUPLICATE KEY UPDATE`` 把 312 条
    upsert 压成**一条**多行 SQL（而不是 312 次 ORM 写）—— 本函数会在**每个**用例前
    被调用（惰性补种），逐条写会拖垮整跑耗时。

    注：Django 的 ``bulk_create(update_conflicts=True, unique_fields=[...])`` 在
    MySQL 后端**不支持**（``NotSupportedError: This database backend does not
    support updating conflicts with specifying unique fields``），故走原生 SQL。
    """
    from django.db import connection as _conn
    from django.db.models import Case, Value, When
    from django.utils import timezone

    from apps.core.management.commands.seed_v2_init import (
        RESOURCE_SUB_MODULES,
        RESOURCES,
        STRATEGY_GOVERNED_CODES,
        SYSTEM,
    )
    from apps.core.models_permission_v2 import PermissionResource

    now = timezone.now()
    with _conn.cursor() as c:
        c.executemany(
            """INSERT INTO permission_resources
               (resource_code, system_code, resource_name, resource_type,
                module, sort_order, status, strategy_governed, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 system_code = VALUES(system_code),
                 resource_name = VALUES(resource_name),
                 resource_type = VALUES(resource_type),
                 module = VALUES(module),
                 sort_order = VALUES(sort_order),
                 status = VALUES(status)""",
            [
                (code, SYSTEM, name, rtype, module, 0, 1, 0, now)
                for code, name, rtype, module in RESOURCES
            ],
        )
    # 受策略管控置位（与 seed_v2_init 主循环之后的两步一致：只置 True、不归零）
    PermissionResource.objects.filter(
        resource_code__in=STRATEGY_GOVERNED_CODES,
    ).update(strategy_governed=True)
    # 子模块展示名置位（无手工编辑入口，seed 恒为真源）
    PermissionResource.objects.filter(
        resource_code__in=RESOURCE_SUB_MODULES,
    ).update(
        sub_module=Case(
            *[
                When(resource_code=code, then=Value(sub))
                for code, sub in RESOURCE_SUB_MODULES.items()
            ],
            default=Value(None),
        ),
    )


def _seed_preset_stages():
    """补齐预置起止阶段（初评 P001 / 正式录用 P099）—— 等价于迁移 process.0012。

    2026-10-21 卡 B5 新增。

    这两行是**迁移**写进库的（``apps/process/migrations/0012_preset_start_end_stages.py``），
    属于已提交数据。而 ``django_db(transaction=True)`` 的用例在 teardown 会
    ``flush`` 整库 —— 连同这些已提交的迁移种子一起清掉；``--reuse-db`` 下次运行
    不会再重跑已应用的迁移，于是「起止阶段」**永久缺失**，后续用例批量报
    ``RecruitmentStage.DoesNotExist``（实测 9 处）+ ``CommandError: 找不到系统内置起止阶段``
    （2 处）。迁移不可重放，所以这里补一个等价的幂等 seed。
    """
    from apps.process.models import RecruitmentStage

    for code, name, is_start, is_end in (
        ('P001', '初评', True, False),
        ('P099', '正式录用', False, True),
    ):
        obj, _created = RecruitmentStage.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'stage_type': 'START_END',
                'is_builtin': True,
                'is_start': is_start,
                'is_end': is_end,
                'status': 'ENABLED',
            },
        )
        # 系统不可变量始终强制正确（与迁移同语义）
        obj.stage_type = 'START_END'
        obj.is_builtin = True
        obj.is_start = is_start
        obj.is_end = is_end
        obj.status = 'ENABLED'
        obj.save(update_fields=['stage_type', 'is_builtin', 'is_start', 'is_end', 'status'])


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

    2026-10-21 整改: 原实现 ``except Exception: pass`` 会把**瞬时**数据库错误
    (MySQL 1213 死锁 / 1205 锁等待超时) 一并吞掉 → 动作字典没补回来 →
    ``is_operable`` 的动作白名单全空 → 候选人写操作(转发/推荐/关注…)一律 403。
    现改为: 瞬时错误退避重试, 仍失败则**记录**并打 warning(不再静默)。
    """
    def _do():
        from apps.data_permission.action_map import sync_seed

        sync_seed()
        # 字典刚被改动 -> 必须失效 TTL 缓存, 否则读到的还是回滚前的旧值
        from apps.data_permission.action_registry import invalidate_cache

        invalidate_cache()

    _run_with_retry(_do, 'seed:action_dictionary')


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup(item):
    """惰性重 seed **动作字典种子**（本 hook 唯一保留的补种）。

    2026-10-21 卡 B5 调整：**不再**在本 hook 里补 role_permission /
    permission_resources / 起止阶段 / 指标种子。

    原因：本 hook 跑在**用例自己的 fixture 之后**（fixture 在 item.setup() 里就绪，
    trylast 的本 hook 在其后执行）。有些用例**故意清空**这三张表来构造「迁移前」的
    受控状态（如 ``apps/core/tests/test_migrate_0028_resource_code_rename.py`` 的
    ``three_stores`` fixture 会 ``PermissionResource.objects.all().delete()``）——
    本 hook 若在其后补种，就会把「迁移前状态」重新填满 → 迁移因「目标码已存在」而
    拒绝执行 → 用例假红（实测 0028 整文件 7 例全红）。

    这些种子的恢复统一交给 ``pytest_runtest_setup``（**tryfirst**，见下）→ 提交态、
    且跑在用例自己的 fixture **之前** → 既保证下一个用例看到完整种子，
    又不干扰本用例的受控状态。
    """
    _seed_action_dictionary()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """在**用例事务之外**修复被 flush 清空的已提交种子（提交态写入）。

    2026-10-21 卡 B5。

    🔴 为什么是 tryfirst 而不是 trylast：
    - trylast 会跑在**用例自己的 fixture 之后**（fixture 在 item.setup() 里就绪），
      于是「故意清空注册表来构造迁移前状态」的用例（``test_migrate_0028_*`` 的
      ``three_stores`` fixture）会被本 hook 重新填满 → 迁移因「目标码已存在」拒绝执行
      → 用例假红；
    - trylast 跑在**用例事务内**，补的种子随用例回滚 → 补了等于没补；
    - 放在 teardown（提交态）则会与**用例事务残留的锁**形成 MySQL 死锁
      （实测 1213 Deadlock → 后续查询全部报「An error occurred in the current
      transaction」→ 一片 403/500）。

    tryfirst 的时机恰好避开全部三个问题：跑在 item.setup() 之前 → 既没有用例事务、
    也没有用例 fixture 的清空动作，写入是**提交态**的、且不会与用例抢锁。

    另外要显式 **unblock 数据库**：pytest-django 默认只在用例体内放行 DB 访问
    （见 ``django_db_blocker``），本 hook 跑在用例之外 → 直接查库会抛
    ``RuntimeError: Database access not allowed``（本 hook 内的异常会被吞掉 →
    补种静默失效）。
    """
    blocker = None
    try:
        from pytest_django.plugin import blocking_manager_key

        blocker = item.config.stash.get(blocking_manager_key, None)
    except Exception:
        blocker = None

    if blocker is None:
        _repair_committed_seeds()
        return
    with blocker.unblock():
        _repair_committed_seeds()


def _seed_demand_dynamic_fields():
    """重放 Demand 动态字段的**数据迁移**（0019 → 0020 → 0022 → 0024 → 0025）。

    2026-10-21 卡 B5 新增。

    与 ``_seed_preset_stages`` 同因：Demand 的规范字段集（29 个 key：5 个复用列
    + 5 个新增系统字段 + 12 个自定义字段 + …）是**迁移**写进库的已提交数据，
    会被 ``django_db(transaction=True)`` 用例的 ``flush`` 清掉；``--reuse-db``
    下次运行不再重跑已应用的迁移 → 字段集永久缺失 →
    ``apps/demand/tests/test_field_structure_alignment.py`` 5 个用例全灭
    （「缺少系统字段 talent_level」/「缺少自定义字段 external_short_name」/ …）。

    迁移不可重放（schema 迁移无法回退），故这里**只重放数据迁移的函数**：
    它们都接受 ``(apps, schema_editor)``，用真实 app registry 调即可
    （``schema_editor`` 传 None —— 这些函数不碰 schema）。
    """
    from importlib import import_module

    from django.apps import apps as dj_apps

    chain = (
        ('apps.dynamic_field.migrations.0019_seed_demand_system_fields', 'seed_demand_system_fields'),
        ('apps.dynamic_field.migrations.0020_demand_system_fields_group_fix', 'fix_demand_system_fields'),
        ('apps.dynamic_field.migrations.0022_seed_demand_jd_requirements', 'seed_jd_requirements'),
        ('apps.dynamic_field.migrations.0024_align_demand_fields_to_spec', 'align_demand_fields'),
        ('apps.dynamic_field.migrations.0025_demand_fields_exact_spec_set', 'prune_legacy_demand_fields'),
    )
    for mod_name, func_name in chain:
        mod = import_module(mod_name)
        getattr(mod, func_name)(dj_apps, None)


def _seed_core_metrics():
    """重放 metrics 的**指标/模板种子**数据迁移。

    2026-10-21 卡 B5 新增（同 ``_seed_demand_dynamic_fields`` 同因）。

    覆盖的种子：
    - 0012 / 0016 / 0020：demand.* / position.* / candidate.* 点路径**原子指标**；
    - 0013 / 0014：平均工作年限**派生指标**；
    - 0017：跳槽频率 / 工作时长**派生指标**；
    - 0018：8 条「安全集合」**指标模板**（性别 / 年龄 / 跳槽频率 …）；
    - 0027 / 0028 / 0029：按动态字段回填指标 + 清洗敏感/自由文本指标。

    它们都是**迁移**写进库的已提交数据，会被 ``flush`` 清掉；缺失后
    ``apps/metrics/tests/test_filterable.py``（3 例）、
    ``apps/metrics/tests/test_entry_condition_integration.py``（2 例）、
    ``apps/metrics/tests/test_template_io.py``（1 例）拿不到指标/模板目录。
    """
    from importlib import import_module

    from django.apps import apps as dj_apps

    chain = (
        ('apps.metrics.migrations.0012_seed_demand_position_object_path_metrics', '_seed'),
        ('apps.metrics.migrations.0016_seed_missing_core_candidate_metrics', '_seed'),
        ('apps.metrics.migrations.0020_seed_position_profile_metrics', '_seed'),
        ('apps.metrics.migrations.0027_backfill_dynamic_field_metrics', '_forwards'),
        ('apps.metrics.migrations.0028_strip_leaked_sensitive_metrics', '_forwards'),
        ('apps.metrics.migrations.0029_strip_freetext_set_operators', '_forwards'),
    )
    for mod_name, func_name in chain:
        try:
            mod = import_module(mod_name)
            getattr(mod, func_name)(dj_apps, None)
        except Exception as exc:  # noqa: BLE001 — 单个种子失败不阻断其余
            # 单个种子失败不阻断其余（历史迁移与当前模型可能有字段漂移）；
            # 但**不再静默** —— 记录下来，避免「字段集永远缺一块」这类问题被反复误判成环境抖动。
            _record_repair_failure(f'seed:demand_dynamic_fields:{mod_name}.{func_name}', exc)
            continue
    # 派生指标 / 安全集模板另走 _seed_safe_set_metrics（0013/0017/0018 引用了
    # 已被 0021 删除的 DerivedMetric.params，无法用当前 registry 重放）
    _seed_safe_set_metrics()


def _seed_dynamic_strategy_grants():
    """重放 core.0034（动态策略资源码注册 + 授予 SUPER_ADMIN/ADMIN）。

    2026-10-21 卡 B5 新增（同因：已提交种子被 flush 清掉）。

    0034 写的 ``role_permission`` 授权行（ADMIN / SUPER_ADMIN × 5 条动态策略码）
    是 ``/auth/me`` 权限清单的来源，缺失后
    ``apps/data_permission/tests/test_dynamic_strategy_scope.py`` 拿不到任何权限码。
    """
    from importlib import import_module

    from django.apps import apps as dj_apps

    mod = import_module('apps.core.migrations.0034_dynamic_strategy_permissions')
    mod.forward(dj_apps, None)


def _seed_safe_set_metrics():
    """补齐「安全集」**派生指标 + 指标模板**（当前 schema 口径）。

    2026-10-21 卡 B5。

    为什么不能直接重放 metrics.0013 / 0017 / 0018：它们是**历史**数据迁移，
    引用的 ``DerivedMetric.params`` 字段已被 0021「calc params 移到模板」删除
    （``RemoveField('derivedmetric', 'params')``）→ 用当前 app registry 重放会抛
    ``FieldError: Invalid field name(s) for model DerivedMetric: 'params'``。
    故此处按**当前 schema** 直接落这几行，口径与 0013 / 0017 / 0018 + 0021 一致：
    计算参数存模板的 ``calc_params``，输出单位存模板的 ``unit``。

    缺失后果：``apps/metrics/tests/test_template_io.py`` 的导入用例引用派生指标
    「跳槽频率」→ 校验不过 → 整个导入 400（实测整跑 1 例）。
    """
    from apps.metrics.models import AtomicMetric, DerivedMetric, MetricTemplate

    # (name, calc_func, unit, description, calc_params)
    derived_specs = (
        ('跳槽频率', 'COUNT_IN_WINDOW', '段', '近N年内工作经历段数（跳槽频率）', {'window_years': 5}),
        ('工作时长', 'TOTAL_WORK_MONTHS', '月', '所有工作经历累计月数', {}),
        ('平均工作时长', 'AVG_WORK_MONTHS', '年', '平均每段工作经历的工作年数；recent_n=0 为全部工作经历平均',
         {'recent_n': 0, 'unit': 'year'}),
    )
    for name, calc_func, unit, desc, _params in derived_specs:
        DerivedMetric.objects.get_or_create(
            name=name,
            defaults={
                'calc_func': calc_func,
                'base_path': 'candidate.workExperience',
                'data_type': 'number',
                'unit': unit,
                'description': desc,
                'status': 'enabled',
            },
        )

    # (模板名, 原子/派生, 指标名, operators, param_enums, calc_params, unit)
    template_specs = (
        ('性别', 'atomic', '性别', ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], ['男', '女'], None, ''),
        ('年龄', 'atomic', '年龄',
         ['IS_EMPTY', 'IS_NOT_EMPTY', 'GT', 'GTE', 'EQ', 'LT', 'LTE', 'BETWEEN'], [], None, ''),
        ('最高学历', 'atomic', '最高学历', ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], [], None, ''),
        ('当前公司', 'atomic', '当前公司', ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], [], None, ''),
        ('需求级别', 'atomic', '需求级别', ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], [], None, ''),
        ('需求职位名称', 'atomic', '需求职位名称', ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], [], None, ''),
        ('职位名称', 'atomic', '职位名称', ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], [], None, ''),
        ('跳槽频率', 'derived', '跳槽频率', ['GTE'], [], {'window_years': 5}, '段'),
        ('工作时长', 'derived', '工作时长', ['GTE'], [], {}, '月'),
        ('平均工作时长', 'derived', '平均工作时长',
         ['GT', 'GTE', 'EQ', 'LT', 'LTE', 'BETWEEN'], [], {'recent_n': 0, 'unit': 'year'}, '年'),
    )
    for tpl_name, kind, metric_name, operators, param_enums, calc_params, unit in template_specs:
        defaults = {
            'operators': operators,
            'param_enums': param_enums,
            'param_config': {},
            'calc_params': calc_params or {},
            'unit': unit,
            'status': 'enabled',
        }
        if kind == 'atomic':
            metric, _ = AtomicMetric.objects.get_or_create(
                name=metric_name,
                defaults={
                    'source_path': 'candidate.extra',
                    'data_type': 'string',
                    'status': 'enabled',
                },
            )
            defaults['atomic_metric'] = metric
        else:
            metric = DerivedMetric.objects.filter(name=metric_name).first()
            if metric is None:
                continue
            defaults['derived_metric'] = metric
        MetricTemplate.objects.get_or_create(name=tpl_name, defaults=defaults)


def _repair_committed_seeds():
    """把「被 flush 清空的已提交种子」补回来 —— **提交态**写入。

    2026-10-21 卡 B5 新增（与 ``pytest_runtest_setup``(tryfirst) 配套）。

    背景：``django_db(transaction=True)`` 的用例在 teardown 会 ``flush`` 整库，连同
    **已提交**的种子一起清掉（permission_resources / 预置起止阶段 / role_permission /
    Demand 动态字段 / 核心指标）；``--reuse-db`` 下次运行不再重跑已应用的迁移 →
    种子永久缺失 → 后续用例批量 ``DoesNotExist`` / 403。迁移不可重放，故在此补
    一个幂等 seed。

    调用时机：``pytest_runtest_setup``(tryfirst) —— 跑在用例事务与用例 fixture 之前，
    写入是提交态的、且不与用例抢锁（详见该 hook 的注释）。

    2026-10-21 整改（整跑 flaky 根因治理）：原实现里哨兵判定与补种都用
    ``except Exception: pass`` **吞掉一切异常** —— 其中包括 MySQL 1213 死锁 /
    1205 锁等待超时这类**瞬时**错误 → 补种静默失效 → 种子没补回来 →
    后续用例集体 403 / DoesNotExist（实测整跑在 0 failed 与 8~18 failed 之间乱跳）。
    现改为：
      ① 异常集**收窄**：只对「瞬时数据库错误」重试；
      ② 瞬时错误**退避重试**（最多 3 次）；
      ③ 重试仍失败 → **记录到 ``_SEED_REPAIR_FAILURES`` 并打 warning**
         （不再静默消失，可用 ``seed_repair_failures()`` 复查）。
    """
    from django.db import connection as _conn

    # 🔴 闸门：**只允许补到测试库**。
    # tryfirst hook 跑在 item.setup() 之前 → pytest-django 还没把库名切成测试库
    # → 此时补种会打到**开发库**（既污染开发库，又因为开发库迁移较旧而报缺列错误）。
    # 这个窗口的补种需求由 session 级 `_ensure_v2_schema` 覆盖（它跑在
    # `django_db_setup` 之后 → 库名已切换）。
    if not in_test_database():
        return

    def _sentinel_present(sql) -> bool:
        """哨兵行是否存在。**无法判定**时按「存在」处理（避免无 DB 的纯单测被误补）。"""
        for attempt in range(1, _REPAIR_MAX_ATTEMPTS + 1):
            try:
                with _conn.cursor() as c:
                    c.execute(sql)
                    return c.fetchone() is not None
            except RuntimeError:
                # pytest-django 的 DB 阻断（无 DB 的纯单测）→ 不需要补
                return True
            except Exception as exc:  # noqa: BLE001 — 下面按是否瞬时分别处理
                if _is_no_db_context(exc):
                    # SimpleTestCase 子类禁止查库 → 本来就不需要补种（不算失败）
                    return True
                if _is_transient_db_error(exc) and attempt < _REPAIR_MAX_ATTEMPTS:
                    time.sleep(_REPAIR_BACKOFF_SECONDS * attempt)
                    continue
                _record_repair_failure(f'sentinel: {sql[:60]}', exc)
                # 瞬时错误且重试用尽 → 判定为「缺失」，交给下面的补种再试一次
                # （补种是幂等 upsert，重复执行不会写脏数据）
                return not _is_transient_db_error(exc)
        return True

    def _reseed(sql, seeder, label=''):
        """哨兵行缺失 → 补种（幂等）。单项失败不阻断其它种子，但**会被记录**。"""
        if _sentinel_present(sql):
            return
        _run_with_retry(seeder, label or sql[:60])

    # 🔴 判定用**哨兵行**而非「表是否为空」：迁移 core.0034 会在 migrate 阶段写入
    # 5 条资源码 + 10 条 role_permission 行 → 表不为空 → 「表空才补」会整批跳过
    # → 注册表只剩 5 条 / HR 一条授权都没有 → 非超管用例整片 403（卡 B5 实测）。
    _reseed(
        "SELECT 1 FROM role_permission WHERE role_code='HR' "
        "AND resource_code='recruit:candidate:list' LIMIT 1",
        lambda: _seed_role_permissions(_conn),
    )
    _reseed(
        "SELECT 1 FROM permission_resources WHERE resource_code='recruit:candidate:list' LIMIT 1",
        _seed_permission_resources,
    )
    _reseed(
        "SELECT 1 FROM recruitment_stages WHERE code='P001' LIMIT 1",
        _seed_preset_stages,
    )
    _reseed(
        "SELECT 1 FROM dynamic_fields WHERE resource='Demand' AND field_key='talent_level' LIMIT 1",
        _seed_demand_dynamic_fields,
    )
    if not _sentinel_present(
        "SELECT 1 FROM metrics_atomic_metric WHERE source_path='candidate.age' LIMIT 1"
    ) or not _sentinel_present(
        "SELECT 1 FROM metrics_derived_metric WHERE name='跳槽频率' LIMIT 1"
    ):
        _run_with_retry(_seed_core_metrics, 'seed:core_metrics')
    _reseed(
        "SELECT 1 FROM role_permission WHERE role_code='ADMIN' "
        "AND resource_code='recruit:settings:dynamic_strategy:list' LIMIT 1",
        _seed_dynamic_strategy_grants,
    )
    # 动作字典（data_permission_actions / _presets）：迁移 0006 灌的已提交种子，
    # 同样会被 flush 清掉。字典为空 → `is_operable` 的「动作白名单」判定全部落空 →
    # 候选人写操作（转发/推荐/关注…）一律 403（实测 7 例 forward/follow 假红）。
    _reseed(
        "SELECT 1 FROM data_permission_actions WHERE `key`='recommend' LIMIT 1",
        _seed_action_dictionary,
    )


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    """用例结束后修复被 flush 清空的已提交种子（提交态写入，详见 _repair_committed_seeds）。

    🔴 必须**显式 unblock 数据库**：pytest-django 在 ``db`` fixture 的 finalizer 里
    ``django_db_blocker.restore()``，把会话级 blocker 恢复成「阻断」态（本插件的设计：
    只在用例体内允许 DB 访问）。本 hook 跑在 finalizer **之后**，此时直接查库会抛
    ``RuntimeError: Database access not allowed`` —— 而 _repair_committed_seeds 内部
    把异常吞掉了，于是「补种子」静默失效：flush 清空注册表后再也没补回来 →
    卡 A1 的 fail-closed 把所有派生写码判为「未注册」→ 非超管写操作一律 403
    （实测整跑 196 failed）。

    修法：借 ``config.stash[blocking_manager_key]`` 拿到同一个 blocker，
    在 ``with blocker.unblock():`` 里补种子（退出时自动 restore 回阻断态）。
    """
    blocker = None
    try:
        from pytest_django.plugin import blocking_manager_key

        blocker = item.config.stash.get(blocking_manager_key, None)
    except Exception:
        blocker = None

    if blocker is None:
        return None
    # 2026-10-21 卡 B5: 这里**不再补种子**。放在 teardown（跑在用例 finalizer 之后）
    # 会与用例事务残留的锁形成 MySQL 死锁（1213 Deadlock）→ 事务 broken → 后续查询
    # 全抛 TransactionManagementError → 一片 403/500（实测 15 failed）。
    # 补种子已移到 pytest_runtest_setup(tryfirst)：用例事务与用例 fixture 之前，
    # 提交态写入、不抢锁、也不干扰用例自己构造的受控状态。
    return None


@pytest.fixture(autouse=True, scope='session')
def _ensure_v2_schema(django_db_setup, django_db_blocker):
    """session 级 autouse: 测试 DB 初始化完后, 强制补 V2 schema + seed 权限表.

    - 补 V2 列 (role_code / system_code / ...) 到 user_roles + roles (兼容 V1 表)
    - seed role_permission 表 (V2 业务 has_perm 查这个, 没 seed 永远 403)

    2026-08-03 T01.1 (寇豆码): 移除 `call_command('migrate', run_syncdb=True)` —
    pytest-django --create-db 已经跑过 migrate, 重复调用不必要. 同时 T01.1 把
    0004_v2_apply_schema 加进迁移图, pytest-django 自然会 apply, 不需要这里手动 migrate.
    """
    with django_db_blocker.unblock():
        _ensure_v2_schema_compat()
        # 2026-08-03 T01.1 (寇豆码): 不再在 session 起始 seed permission_resources /
        # permission_templates (那会破坏 test_bootstrap 测试 — 它假设空 DB).
        # test_sync_resources_t29 改由 test_sync_resources_empty_array_clears 显式
        # call_command('seed_v2_init') 提供 seed, 这条用例仍能跑通; 其他两条
        # (test_sync_resources_persists_codes / test_sync_resources_rejects_invalid_codes)
        # 暂时仍依赖 QUARANTINE 隔离 (RT-2 验收将由 T01.2/T05 解决).
        # ---- seed role_permission: HR/HRBP/SUPER_ADMIN 都有 recruit:domain:list 权限 ----
        # 复用 _seed_role_permissions（幂等 upsert，故**无条件**执行一次）。
        # 原来只在「表为空」时播种：迁移 core.0034 在 migrate 阶段就写了 10 行
        # （SUPER_ADMIN / ADMIN × 动态策略 5 码）→ 表不为空 → 整批播种被跳过 →
        # HR / HRBP 一条授权都没有 → 非超管用例整片 403（卡 B5 实测）。
        _seed_role_permissions(connection)
        # 注: roles.default_data_scope_type=ALL 在 _create_role_v2 里设, 这里不再 UPDATE
        # (因为 session fixture 跑得比 function fixtures 早, 当时 roles 表还是空的)
        # ---- 卡 B5（2026-10-21）：补齐「已提交种子」三件套 ----
        # ① permission_resources：资源码注册表。**不写** templates / tenant_config ——
        #    那两张表由 seed_v2_init 命令负责，且 test_bootstrap_missing_template_raises
        #    明确依赖「模板为空」这一前提。
        # ② recruitment_stages 的预置起止阶段：等价于迁移 process.0012（迁移不可重放）。
        # 这三者都是**已提交**数据，会被 django_db(transaction=True) 用例的 flush 清掉，
        # 故在 session 起始先落一次（提交态），并由 pytest_runtest_setup(tryfirst) 负责修复。
        _repair_committed_seeds()


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

    测试库统一 V2 fresh schema（MySQL），只写 V2 列（id=BigAuto + system_code/role_code/
    role_name 等，无 V1 列）。V1 / SQLite 历史分支已随「禁用 SQLite」移除。

    2026-10-21 (卡 B5): 改为**幂等 upsert**（先查后写），不再裸 INSERT。

    为什么必须改：``apps/campus_rotation/apps.py`` 的 post_migrate 回调
    （``_seed_campus_roles_on_post_migrate`` → ``apps/campus_rotation/seeds.py:112-155``）
    会在 **migrate 阶段**用 ``update_or_create`` 幂等预置 4 个系统角色 ——
    CAMPUS_MENTOR / HEAD_TEACHER / **HRBP** / CLASS_MONITOR。
    这些行是**已提交**的：既不随用例事务回滚，也不随 ``--reuse-db`` 重建库而消失。

    于是 ``hrbp_role`` fixture 的裸 INSERT 必然撞 ``roles.uk_system_role``：
    实测整跑 128 处 ``IntegrityError: Duplicate entry 'recruit-HRBP' for key
    'roles.uk_system_role'``，凡是用 ``hrbp_user`` 的用例在 **setup 阶段**整片 error。

    冲突时**按 fixture 声明的值覆盖**（role_name / description / is_system / status /
    default_data_scope_type），而不是「保留种子行不动」—— 因为 fixture 的契约就是
    「本次要的就是这个状态（scope=ALL）」，与冲突前裸 INSERT 落库的值完全一致；
    若保留种子行（HRBP 的 DEPT_AND_SUB），反而会让用例读到与 fixture 声明不符的 scope，
    把「种子残留」变成「用例结果依赖库的历史状态」——那才是真正的跨用例污染。

    注：MySQL 9.x 已不保证 ``ON DUPLICATE KEY UPDATE ... VALUES(col)`` 语法可用，
    故这里显式 SELECT → UPDATE / INSERT，不用 upsert 语法糖。
    """
    from django.utils import timezone
    now = timezone.now()
    with connection.cursor() as c:
        # 测试库统一 V2 fresh schema（MySQL），只写 V2 列
        c.execute(
            "SELECT id FROM roles WHERE system_code='recruit' AND role_code=%s LIMIT 1",
            [code],
        )
        if c.fetchone():
            c.execute(
                """UPDATE roles
                      SET role_name=%s, description='', is_system=0, status=1,
                          default_data_scope_type='ALL', updated_at=%s
                    WHERE system_code='recruit' AND role_code=%s""",
                [name, now, code],
            )
        else:
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
    """V2 → raw SQL 写 user_roles（V1 / SQLite 路径已移除，统一走 V2 fresh schema）。"""
    _raw_attach_v2_role(user, role)


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
