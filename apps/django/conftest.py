"""v2 权限模块全局 pytest fixtures.

注意: 已有 tests/conftest.py 提供 hr_user / hrbp_user / super_user / auth_client
等基础 fixtures (Phase 1C). 这里只补充 v2 权限重写专用的 IDOR 跨部门测试 fixtures,
不重复定义同名 fixture 以避免覆盖.

v2 权限 IDOR 测试需要两个不同部门的 HR 用户, 用于验证:
  - HR(dept_a) 不能看到 dept_b 的数据
  - HR(dept_b) 不能看到 dept_a 的数据

2026-08-03 R7 (寇豆码): pytest.ini 的 testpaths 从 `tests` 放开为 `tests apps`,
把 apps/*/tests/ 下 127 个用例 (含全部 V2 权限 / IDOR 回归) 纳入收集.

  原 `tests/conftest.py` 是 `apps/*/tests/` 的 **sibling** 而非 ancestor, pytest
  只向目录树上方查找 conftest, 所以 app 内测试拿不到 hr_user / super_user /
  auth_client 等基础 fixture. 原方案是在 add_candidate / talent_pool 的子
  conftest 里写 `pytest_plugins = ['tests.conftest']`, 有两个问题:
    1. pytest 8+ 已禁止在非顶层 conftest 声明 pytest_plugins (它实际影响全量
       测试, 语义有误导性), 收集阶段直接报错;
    2. 即使上提到本文件, 同一个 `tests/conftest.py` 会被 pytest 同时按
       "conftest" 和 "plugin" 两种身份注册, 抛 ValueError.
  最终方案: 把共享 fixtures 从 `tests/conftest.py` 改名为普通模块
  `tests/fixtures_common.py`, 在这里以 plugin 身份全局加载一次.
"""
import os
import time

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

# 全局引入基础 fixtures (hr_user / super_user / auth_client / department /
# hr_role ... 以及 session 级 _ensure_v2_schema), 使 tests/ 与 apps/*/tests/
# 共用同一套. 必须声明在 rootdir 顶层 conftest —— pytest 8+ 不允许在子 conftest 声明.
pytest_plugins = ['tests.fixtures_common']

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


def pytest_configure(config):
    """给 ``tmp_path`` 一个**每轮唯一**的 basetemp（除非命令行显式指定）。

    2026-10-21 整跑 flaky 根因治理。

    背景：pytest.ini 曾把 ``--basetemp`` 写死成 ``/tmp/ats_pytest_bt``。pytest 的
    ``_ensure_relative_to_basetemp`` 对**已存在**的 basetemp 会先 ``rm_rf`` 再
    ``mkdir`` → 沙箱拦删除 → ``PermissionError: [Errno 1] Operation not permitted``
    → 所有用 ``tmp_path`` 的用例在 **setup 阶段**整片 error（实测一次整跑 12 例）。

    改成「每轮唯一的新目录」后：
      ① 目录不存在 → 只需 ``mkdir``（沙箱放行新建），不需要删旧目录；
      ② 并发的两轮整跑不会互相覆盖对方的临时文件。

    放在 ``/tmp`` 下是为了绕开沙箱对 ``/private/var/folders/.../pytest-of-*`` 的拦截
    （pytest.ini 注释里记的同一个坑）。
    """
    if config.option.basetemp:
        return  # 命令行显式指定 → 尊重调用方
    config.option.basetemp = f'/tmp/ats_pytest_bt_{os.getpid()}_{int(time.time())}'


@pytest.fixture
def dept_a(db):
    """部门 a - 用于跨部门 IDOR 测试."""
    from apps.core.models import Department
    return Department.objects.create(id='dept-a-v2', name='部门A-V2', code='dept_a_v2', path='/部门A-V2')


@pytest.fixture
def dept_b(db):
    """部门 b - 用于跨部门 IDOR 测试."""
    from apps.core.models import Department
    return Department.objects.create(id='dept-b-v2', name='部门B-V2', code='dept_b_v2', path='/部门B-V2')


@pytest.fixture
def hr_dept_a(db, dept_a):
    """HR 用户, 部门 a. 应当只看到 dept_a 的数据."""
    u, _ = User.objects.get_or_create(
        username='hr_dept_a',
        defaults={
            'is_active': True,
            'department': dept_a,
            'first_name': 'HrA',
            'last_name': 'A',
        },
    )
    u.set_password('hr123')
    u.save()
    return u


@pytest.fixture
def hr_dept_b(db, dept_b):
    """HR 用户, 部门 b. 应当只看到 dept_b 的数据."""
    u, _ = User.objects.get_or_create(
        username='hr_dept_b',
        defaults={
            'is_active': True,
            'department': dept_b,
            'first_name': 'HrB',
            'last_name': 'B',
        },
    )
    u.set_password('hr123')
    u.save()
    return u