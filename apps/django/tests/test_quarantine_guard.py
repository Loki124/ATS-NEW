"""隔离区双向守卫.

背景 (2026-10-08 审查 #28 + ARCH_DECISION 的教训):
    原先的隔离名单由 GitHub 仓库级 QUARANTINE 环境变量承载 —— **不在代码库内**,
    不能 review、不能审计, 9 条里已自愈的会被无限期静默跳过 (本项目第二次踩此坑)。
    现已改为代码内 marker: 给用例打 `@pytest.mark.quarantine`, CI 用 `-m "not quarantine"` 排除。

    但 marker 本身也会腐烂:
    - 自愈的用例一直挂着 marker 却不跑 → 等于没测 (单向守卫的漏洞);
    - 有人挂了 marker 却没登记到 QUARANTINED_TESTS (本清单) → 失去审计入口。

    本文件做**双向守卫**:
    1. QUARANTINED_TESTS 是隔离区的唯一真相源; 为空时表示"无已知失败"。
    2. 任一隔离项若实际**通过** → 说明已自愈, 本测试**硬失败**, 逼你把节点移出清单并去掉 marker。
    3. 任一带 `quarantine` marker 的用例若不在 QUARANTINED_TESTS 里 → 本测试失败, 逼你登记。
"""
import subprocess
import sys

import pytest

# === 隔离区唯一真相源 =============================================================
# 加隔离: 1) 用例上加 @pytest.mark.quarantine
#         2) 把完整 nodeid (如 apps/xxx/tests/test_y.py::TestA::test_b) 加入本列表
# 解除隔离: 修好后删除 nodeid + 去掉 marker。CI 用 `-m "not quarantine"` 自动排除。
QUARANTINED_TESTS: list[str] = []


def _django_env():
    import os
    env = os.environ.copy()
    env.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
    return env


def _run_node(nodeid: str) -> int:
    """单独跑一个 nodeid, 返回退出码 (0=通过)。"""
    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', nodeid, '-q', '-p', 'no:cacheprovider',
         '--no-header', '--tb=no'],
        cwd='apps/django' if False else _repo_root(),
        env=_django_env(),
        capture_output=True,
        text=True,
    )
    return proc.returncode


def _repo_root() -> str:
    # tests/ 位于 apps/django/tests, 仓库根在 apps/django 的上两级。
    from pathlib import Path
    return str(Path(__file__).resolve().parents[2])


def _collect_quarantined_nodeids() -> set[str]:
    """收集所有带 @pytest.mark.quarantine 的用例 nodeid。"""
    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', '--collect-only', '-q',
         '-m', 'quarantine', '-p', 'no:cacheprovider', '--co'],
        cwd=_repo_root(),
        env=_django_env(),
        capture_output=True,
        text=True,
    )
    nodeids = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.endswith('::') or not line:
            continue
        # pytest --collect-only -q 输出形如:  apps/x/tests/t.py::Test::test
        if '::' in line and not line.startswith(('=')):
            nodeids.add(line)
    return nodeids


# ----------------------------------------------------------------- 双向守卫

def test_quarantine_list_matches_markers():
    """带 quarantine marker 的用例必须全部登记在 QUARANTINED_TESTS 里。"""
    if not QUARANTINED_TESTS:
        pytest.skip('隔离区为空, 无标记需核对')
    marked = _collect_quarantined_nodeids()
    missing = marked - set(QUARANTINED_TESTS)
    assert not missing, (
        f'以下用例挂了 @pytest.mark.quarantine 却未登记进 QUARANTINED_TESTS: {missing}\n'
        f'请补登或去掉 marker。'
    )


def test_quarantine_still_failing():
    """隔离项必须仍真的失败; 一旦自愈, 本测试硬失败逼你解除隔离。"""
    if not QUARANTINED_TESTS:
        pytest.skip('隔离区为空, 无项需验证')
    stale = []
    for nodeid in QUARANTINED_TESTS:
        code = _run_node(nodeid)
        if code == 0:
            stale.append(nodeid)
    assert not stale, (
        f'隔离区已有用例自愈 (测试通过), 应从 QUARANTINED_TESTS 移除并去掉 marker: {stale}'
    )


def test_quarantine_marker_is_registered():
    """quarantine marker 必须在 pytest.ini 登记, 否则 --strict-markers 会报警。"""
    # 仅作存在性声明; 真正的注册在 pytest.ini。这里防止误删 ini 条目后无提示。
    from pathlib import Path
    ini = Path(__file__).resolve().parents[1] / 'pytest.ini'
    assert 'quarantine' in ini.read_text(encoding='utf-8'), 'pytest.ini 缺少 quarantine marker 登记'
