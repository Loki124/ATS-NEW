"""T02 回归测试：makemigrations --check 不报错 → 元数据漂移归零。

设计文档 §T02 / QA 验证报告 §A 实测：candidate / gdpr / integration
三个 app 在 Phase 2 之前均存在元数据漂移 (help_text / verbose_name /
索引改名)。 Phase 2 T02 已生成新迁移收口, 本测试作为长期护栏防止
后续 PR 重新引入漂移。

测试方式:
- 对每个 app 分别跑 ``manage.py makemigrations <app> --check --dry-run``,
  期望进程返回码 0 且 stdout 无 "Migrations for" 字样。
- 直接 ``makemigrations --check --dry-run`` 用 |tail 判断退出码会失效
  (见设计文档 §1.3 度量陷阱: tail 的退出码恒为 0), 故用
  subprocess.run + 显式判断 returncode。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


# 本测试通过 subprocess 跑 makemigrations --check, 本身不需要 DB 写权限,
# 但本仓 pytest.ini 的 autouse fixture _ensure_v2_schema (在
# tests/fixtures_common.py:154) 会无条件访问测试 DB. 必须挂 django_db
# 触发 DB 初始化让该 fixture 通过 (与 apps/candidate/tests/test_migration_0005.py
# 同套 init 路径). 详见设计文档 §T02.
pytestmark = pytest.mark.django_db


SETTINGS = 'config.settings.test'


def _django_dir() -> Path:
    """定位 apps/django 目录 (manage.py 所在)。

    本文件位于 .../apps/django/apps/candidate/tests/, 向上数 4 层到 apps/django。
    """
    return Path(__file__).resolve().parents[3]


def _venv_python() -> Path:
    """apps/django/.venv/bin/python 解释器; 不存在则退回 sys.executable。

    CI 镜像 (.github/workflows/ci.yml) 通常走 .venv, 但单测机上若有
    系统 venv 也可手动覆盖 --prefer-virtualenv。这里只兜底。
    """
    v = _django_dir() / '.venv' / 'bin' / 'python'
    return v if v.exists() else Path(sys.executable)


def _run_makemigrations(app_name: str | None = None) -> tuple[int, str]:
    """调子进程跑 makemigrations --check --dry-run 返回 (rc, stdout+stderr)。

    ``app_name=None`` 表示跑全局检查; 否则只查指定 app。
    """
    env = os.environ.copy()
    env['DJANGO_SETTINGS_MODULE'] = SETTINGS

    cmd = [
        str(_venv_python()),
        'manage.py',
        'makemigrations',
    ]
    if app_name:
        cmd.append(app_name)
    cmd += ['--check', '--dry-run']

    proc = subprocess.run(
        cmd,
        cwd=str(_django_dir()),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, (proc.stdout or '') + (proc.stderr or '')


@pytest.mark.parametrize(
    'app_name',
    ['candidate', 'gdpr', 'integration'],
)
def test_makemigrations_check_passes(app_name: str):
    """每个 app 的 makemigrations --check 必须返回 0, 无 'Migrations for' 输出。

    设计文档 §T02 验收标准 1: 三个 app 各自无 pending migration。
    若有人误改 model 字段 (help_text / verbose_name 等元数据), 本测试会
    在 CI 第一时间变红, 阻止 drift 再次累积。
    """
    rc, output = _run_makemigrations(app_name)
    assert rc == 0, (
        f'makemigrations --check --dry-run for {app_name!r} failed (rc={rc}).\n'
        f'Output:\n{output}\n'
        f'如果这是有意修改, 请跑 makemigrations {app_name} 生成新迁移后提交。'
    )
    # 双重保险: 即便 rc 偶发 0 但有漂移输出, 仍然失败 (防御子进程退出码异常)
    assert 'Migrations for' not in output, (
        f'makemigrations for {app_name!r} detected drift but exited 0.\n'
        f'Output:\n{output}'
    )


def test_makemigrations_check_global_no_drift():
    """全局 makemigrations --check --dry-run 也必须无漂移 (兜底)。

    覆盖未来新增的第三个 app (比如 evaluation / search) 时, 这个测试
    会比参数化列表更早报警。注意: 这是回归性兜底, 设计文档 §T02
    验收 #1 的硬约束是全局 0 输出。
    """
    rc, output = _run_makemigrations(app_name=None)
    assert rc == 0, (
        f'global makemigrations --check returned {rc}.\n'
        f'Output:\n{output}'
    )
    assert 'Migrations for' not in output, (
        f'global makemigrations detected drift:\n{output}'
    )
