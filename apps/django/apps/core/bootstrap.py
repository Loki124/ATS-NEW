"""V2 权限系统启动校验.

由 ``AppConfig.ready()`` 调用. 两种"不完整"状态语义必须严格区分:

===========================  ==================  ============================
状态                          行为                 原因
===========================  ==================  ============================
表不存在(未 migrate/全新库)    跳过(skip)           数据库尚未就绪, 不是脏部署
表存在但数据缺失              抛 ImproperlyConfigured  迁移已跑但种子数据缺失,
                                                  属于脏部署, 必须拦住
===========================  ==================  ============================

分层约束 (2026-09 BUGFIX: ``migrate`` 崩溃 no such table: permission_templates):
- ``ready()`` 是**进程级装配钩子**, 在 ``migrate`` / ``makemigrations`` /
  ``collectstatic`` / ``shell`` 等管理命令之前执行. 彼时业务表可能根本不存在,
  因此 ready() 路径**禁止无条件查询业务表**, 必须先做存在性探测.
- 反过来, 若"表已建但种子数据没跑", 任何非初始化命令都不应被放行 —— 否则
  生产上缺 4 个系统模板/资源 < 50 的脏库会被静默投入使用.

跳过规则(两条, 均返回 skipped 而非抛错):
1. 正在执行部署/初始化类管理命令 (migrate / seed_v2_init / collectstatic ...)
   —— 避免"表已建但没种子 → 无法运行 seed 命令"的死锁.
2. 数据库不可达, 或三张必需表尚未创建.
"""
import logging
import os
import sys
from typing import NamedTuple

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

REQUIRED_TEMPLATES = ['TMPL_ADMIN', 'TMPL_DIRECTOR', 'TMPL_SPECIALIST', 'TMPL_INTERVIEWER']
REQUIRED_TENANT_CONFIG_KEY = 'GLOBAL_DEFAULT_DATA_SCOPE'
MIN_RESOURCE_COUNT = 50

#: bootstrap_permission_v2() 的返回状态
BOOTSTRAP_OK = 'ok'
BOOTSTRAP_SKIPPED = 'skipped'

#: 这类管理命令要么负责建库建表, 要么负责灌种子数据, 要么根本不需要数据库.
#: 它们启动时数据库处于"合法的不完整状态", 守卫必须让路, 否则会出现
#: "表已建但缺种子 → migrate/seed 都跑不起来 → 永远补不上种子"的死锁.
BOOTSTRAP_SKIP_COMMANDS = frozenset({
    # ---- schema / 部署 ----
    'migrate', 'makemigrations', 'showmigrations', 'sqlmigrate', 'squashmigrations',
    'collectstatic', 'createcachetable', 'check', 'diffsettings',
    # ---- 数据初始化 / 运维 ----
    'seed_v2_init', 'migrate_v2_data', 'migrate_v2_drop_old',
    'init_demo_v2',
    'flush', 'loaddata', 'dumpdata',
    'createsuperuser', 'changepassword', 'shell', 'dbshell', 'test',
})

#: 识别 manage.py / django-admin 入口, 用于判断当前是否在跑管理命令
_MANAGEMENT_ENTRY_POINTS = frozenset({
    'manage.py', 'django-admin', 'django-admin.py', 'django',
})


class BootstrapResult(NamedTuple):
    """bootstrap_permission_v2() 的执行结果.

    Attributes:
        status: BOOTSTRAP_OK 或 BOOTSTRAP_SKIPPED.
        reason: skipped 的原因描述, ok 时为空串.
    """

    status: str = BOOTSTRAP_OK
    reason: str = ''


def current_management_command() -> str:
    """返回当前正在执行的管理命令名; 非 manage.py/django-admin 入口时返回 ''.

    gunicorn / uwsgi / celery 等长驻进程入口不会命中, 因此生产 Web/Celery
    进程仍会正常执行守卫.

    Returns:
        str: 形如 'migrate' / 'shell'; 不是管理命令时为 ''.
    """
    argv = list(sys.argv) if sys.argv else []
    if not argv:
        return ''
    if os.path.basename(argv[0]) not in _MANAGEMENT_ENTRY_POINTS:
        return ''
    # 跳过 `manage.py` 之后的选项(如 --settings=xxx), 取第一个位置参数
    for arg in argv[1:]:
        if arg.startswith('-'):
            continue
        return arg
    return ''


def _required_tables() -> tuple:
    """从模型 Meta 派生必需表名, 避免与 db_table 定义漂移."""
    from .models_permission_v2 import PermissionResource, PermissionTemplate, TenantConfig
    return (
        PermissionTemplate._meta.db_table,
        PermissionResource._meta.db_table,
        TenantConfig._meta.db_table,
    )


def bootstrap_permission_v2() -> BootstrapResult:
    """服务启动时由 AppConfig.ready() 调用, 校验 V2 权限不变量.

    三重校验: 4 个系统模板存在 / 资源数 >= 50 / 全局默认 scope 配置存在.

    Returns:
        BootstrapResult: status=ok 表示校验通过; status=skipped 表示数据库
        尚未就绪或正在跑初始化命令, 已跳过(不视为通过, 但不阻断启动).

    Raises:
        ImproperlyConfigured: 三张表均已存在, 但模板/资源/配置任一缺失.
            这是脏部署, 必须阻断.
    """
    from django.db import connection
    from django.db.utils import DatabaseError

    # ---- 闸门 1: 部署/初始化类管理命令直接让路 ----
    command = current_management_command()
    if command in BOOTSTRAP_SKIP_COMMANDS:
        return BootstrapResult(BOOTSTRAP_SKIPPED, f'management command: {command}')

    # ---- 闸门 2: 数据库不可达(未建库/服务未起)→ 跳过, 不阻断管理命令 ----
    try:
        existing_tables = set(connection.introspection.table_names())
    except DatabaseError as exc:
        return BootstrapResult(
            BOOTSTRAP_SKIPPED,
            f'database not reachable: {exc.__class__.__name__}',
        )

    # ---- 闸门 3: 表尚未建(全新库/migrate 之前)→ 跳过 ----
    missing_tables = [t for t in _required_tables() if t not in existing_tables]
    if missing_tables:
        logger.warning(
            '[bootstrap_v2] 跳过校验: 表尚未创建 %s (通常出现在全新库执行 migrate 之前)',
            missing_tables,
        )
        return BootstrapResult(BOOTSTRAP_SKIPPED, f'tables not migrated: {missing_tables}')

    # ---- 表已就绪: 以下三项缺失属于脏部署, 必须抛错阻断 ----
    from .models_permission_v2 import PermissionResource, PermissionTemplate, TenantConfig

    missing = [t for t in REQUIRED_TEMPLATES if not PermissionTemplate.objects.filter(
        template_code=t, is_system=1, status=1).exists()]
    if missing:
        raise ImproperlyConfigured(f'V2 templates missing: {missing}')

    cnt = PermissionResource.objects.filter(status=1).count()
    if cnt < MIN_RESOURCE_COUNT:
        raise ImproperlyConfigured(f'V2 resources only {cnt}, need >= {MIN_RESOURCE_COUNT}')

    if not TenantConfig.objects.filter(
        config_key=REQUIRED_TENANT_CONFIG_KEY, system_code='recruit').exists():
        raise ImproperlyConfigured(f'tenant_config {REQUIRED_TENANT_CONFIG_KEY} missing')

    return BootstrapResult(BOOTSTRAP_OK, '')
