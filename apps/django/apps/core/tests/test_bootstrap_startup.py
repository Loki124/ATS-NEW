"""V2 权限启动守卫 (AppConfig.ready()) 的回归 + 变异测试.

背景 BUG (2026-09, 全新 SQLite 库执行 `manage.py migrate` 崩溃)::

    django.db.utils.OperationalError: no such table: permission_templates

根因: `ready()` 是进程级装配钩子, 在 migrate 之前执行, 却直接查业务表.

本文件锁死两件事 (缺一即视为回归):
1. **表不存在 → 跳过**: 全新库/未迁移库执行 ready() 或 migrate 不得崩溃.
2. **表存在但数据缺失 → 报错**: 守卫没有被"跳过"逻辑误伤成空壳,
   生产 MySQL 上的脏部署仍必须被 ImproperlyConfigured 拦住.

变异测试三态 (见 docs 报告):
- 红: revert 掉 `_required_tables()` 存在性探测 → 本文件用例失败
- 绿: 修复后全部通过
- 红: 再把守卫改成"无论如何都 skip" → `test_ready_raises_*` 用例失败
"""
import os
import subprocess
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import override_settings

from apps.core import bootstrap
from apps.core.apps import CoreConfig
from apps.core.models_permission_v2 import (
    PermissionResource,
    PermissionTemplate,
    TenantConfig,
)

#: 三张必需表的真实 DB 表名，与 bootstrap._required_tables() 同源派生，避免漂移。
#: bootstrap.py 仅暴露私有 _required_tables()，此处按测试语义显式列出。
REQUIRED_TABLES = (
    PermissionTemplate._meta.db_table,
    PermissionResource._meta.db_table,
    TenantConfig._meta.db_table,
)

#: apps/django 目录 (本文件位于 apps/django/apps/core/tests/)
DJANGO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


def _run_management_command(args, db_path):
    """在全新 SQLite 库上以子进程执行管理命令, 返回 CompletedProcess."""
    env = dict(os.environ)
    env.update({
        'DJANGO_SETTINGS_MODULE': 'config.settings.dev',
        'DATABASE_URL': f'sqlite:///{db_path}',  # 3 个斜杠 + 绝对路径首个 / = sqlite:////abs
        'PERMISSION_V2_BOOTSTRAP_DISABLED': '0',  # 守卫开启, 不得靠开关绕过
    })
    return subprocess.run(
        [sys.executable, 'manage.py'] + args,
        cwd=DJANGO_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )



def _seed_full_v2_data():
    """补齐 4 模板 + 50 资源 + tenant config, 使守卫校验通过."""
    for code in bootstrap.REQUIRED_TEMPLATES:
        PermissionTemplate.objects.update_or_create(
            template_code=code,
            defaults={
                'system_code': 'recruit',
                'template_name': code,
                'is_system': 1,
                'permission_codes': ['recruit:candidate:list'],
                'status': 1,
            },
        )
    TenantConfig.objects.update_or_create(
        system_code='recruit',
        config_key=bootstrap.REQUIRED_TENANT_CONFIG_KEY,
        defaults={'config_value': 'SELF'},
    )
    PermissionResource.objects.bulk_create([
        PermissionResource(
            system_code='recruit',
            resource_code=f'recruit:bootstrap{i}:menu:view',
            resource_name=f'R{i}',
            resource_type='MENU',
            module='test',
            status=1,
        )
        for i in range(bootstrap.MIN_RESOURCE_COUNT)
    ], ignore_conflicts=True)


def _fresh_core_config():
    """构造一个 CoreConfig 实例用于直接调用 ready()."""
    import apps.core
    return CoreConfig('apps.core', apps.core)


# ---------------------------------------------------------------- 守卫: 跳过


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_bootstrap_skipped_when_tables_not_migrated(monkeypatch):
    """表不存在 → 跳过, 不得抛 OperationalError.

    通过 monkeypatch _required_tables() 返回不存在的表名, 模拟"全新库 / 尚未 migrate"
    时 introspection 探测到必需表缺失的分支 —— 这正是守卫防止 no such table 崩溃的路径.
    (物理 DROP 三张表在 SQLite + Django 测试事务下会触发 FK 约束编辑器报错, 故用等价模拟.)
    """
    monkeypatch.setattr(
        bootstrap, '_required_tables',
        lambda: ('__ats_bootstrap_nonexistent_table__',),
    )

    result = bootstrap.bootstrap_permission_v2()

    assert result.status == bootstrap.BOOTSTRAP_SKIPPED
    assert 'tables not migrated' in result.reason


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_ready_does_not_crash_on_fresh_database(monkeypatch):
    """回归 BUG 本体: 全新库上执行 ready() 不得因 no such table 崩溃.

    模拟"表未建"分支 + 强制开启守卫(test.py 默认 PERMISSION_V2_BOOTSTRAP_DISABLED=True
    会令 ready() 直接 return), 验证 ready() 走跳过路径而不抛错. 真实 DB 的端到端复现
    见 test_migrate_on_brand_new_sqlite_db_exits_zero.
    """
    monkeypatch.setattr(
        bootstrap, '_required_tables',
        lambda: ('__ats_bootstrap_nonexistent_table__',),
    )
    with override_settings(PERMISSION_V2_BOOTSTRAP_DISABLED=False):
        _fresh_core_config().ready()  # 不得抛 OperationalError / ImproperlyConfigured


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_bootstrap_skipped_for_management_commands(monkeypatch):
    """migrate/makemigrations/collectstatic/shell 等命令一律跳过, 避免死锁."""
    for command in ('migrate', 'makemigrations', 'collectstatic', 'shell', 'seed_v2_init'):
        monkeypatch.setattr(bootstrap, 'current_management_command', lambda: command)
        result = bootstrap.bootstrap_permission_v2()
        assert result.status == bootstrap.BOOTSTRAP_SKIPPED, command
        assert command in result.reason


# ---------------------------------------------------------------- 守卫: 报错


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_ready_raises_when_tables_exist_but_data_missing():
    """表已建但数据缺失 → 脏部署, 必须 ImproperlyConfigured 阻断."""
    assert set(REQUIRED_TABLES).issubset(set(connection.introspection.table_names()))

    with override_settings(PERMISSION_V2_BOOTSTRAP_DISABLED=False):
        with pytest.raises(ImproperlyConfigured, match='V2 templates missing'):
            _fresh_core_config().ready()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_ready_raises_when_resources_insufficient():
    """模板齐但资源 < 50 → 阻断. 证明跳过逻辑没有误伤第二重校验."""
    _seed_full_v2_data()
    PermissionResource.objects.filter(module='test').delete()
    PermissionResource.objects.create(
        system_code='recruit', resource_code='recruit:only:one',
        resource_name='only', resource_type='MENU', module='test', status=1,
    )

    with override_settings(PERMISSION_V2_BOOTSTRAP_DISABLED=False):
        with pytest.raises(ImproperlyConfigured, match='V2 resources only 1, need >= 50'):
            _fresh_core_config().ready()


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_bootstrap_ok_when_data_complete():
    """4 模板 + 50 资源 + tenant config 齐 → status=ok."""
    _seed_full_v2_data()

    result = bootstrap.bootstrap_permission_v2()

    assert result.status == bootstrap.BOOTSTRAP_OK
    assert result.reason == ''


# ------------------------------------------------------- 端到端: 全新库 migrate


@pytest.mark.v2_permission
def test_migrate_on_brand_new_sqlite_db_exits_zero(tmp_path):
    """硬证据: 全新空 SQLite 库执行 manage.py migrate 必须退出码 0.

    这是 BUG 的原生复现路径 —— 修复前这里会得到
    `OperationalError: no such table: permission_templates`.
    """
    project_root = str(tmp_path)
    db_path = str(tmp_path / 'fresh.sqlite3')
    env = dict(os.environ)
    env.update({
        'DJANGO_SETTINGS_MODULE': 'config.settings.dev',
        'DATABASE_URL': f'sqlite:///{db_path}',  # 绝对路径 (sqlite:////abs)
        'PERMISSION_V2_BOOTSTRAP_DISABLED': '0',  # 守卫开启, 不得靠开关绕过
        'PYTHONPATH': project_root,
    })
    django_dir = DJANGO_DIR

    proc = subprocess.run(
        [sys.executable, 'manage.py', 'migrate', '--noinput'],
        cwd=django_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )

    assert proc.returncode == 0, (
        f'migrate 失败 (exit={proc.returncode})\n'
        f'--- stdout ---\n{proc.stdout[-3000:]}\n'
        f'--- stderr ---\n{proc.stderr[-3000:]}'
    )
    assert 'no such table' not in (proc.stdout + proc.stderr)
    assert os.path.exists(db_path), 'migrate 应真实建出库文件'


@pytest.mark.v2_permission
def test_makemigrations_on_brand_new_sqlite_db_exits_zero(tmp_path):
    """makemigrations 不得因数据库未就绪而崩溃."""
    db_path = str(tmp_path / 'fresh_mm.sqlite3')
    env = dict(os.environ)
    env.update({
        'DJANGO_SETTINGS_MODULE': 'config.settings.dev',
        'DATABASE_URL': f'sqlite:///{db_path}',
        'PERMISSION_V2_BOOTSTRAP_DISABLED': '0',
    })
    django_dir = DJANGO_DIR

    proc = subprocess.run(
        [sys.executable, 'manage.py', 'makemigrations', '--check', '--dry-run', '--noinput'],
        cwd=django_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )

    # --check 在无变更时退出 0, 有未生成迁移时退出 1; 两者都不是崩溃
    assert proc.returncode in (0, 1), (
        f'makemigrations 异常退出 (exit={proc.returncode})\n{proc.stderr[-3000:]}'
    )
    assert 'no such table' not in (proc.stdout + proc.stderr)
