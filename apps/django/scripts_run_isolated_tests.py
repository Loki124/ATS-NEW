"""用**独立测试库**跑 pytest —— 隔离掉「共享测试库被并发改动」造成的整跑不可复现。

为什么需要它（2026-10-21 整跑 flaky 根因治理）：

`pytest --reuse-db` 下所有 pytest 进程**共用同一个 test 库**。一旦有第二个进程
（另一个会话 / 另一个 agent / 另一个分支的 CI）同时往这个库上应用迁移或跑用例，
就会出现：

  * ``(1213, 'Deadlock found when trying to get lock')`` 死锁；
  * ``(1060, "Duplicate column name 'x'")`` 同一迁移被两个进程同时应用；
  * 失败集合**逐轮不同**（403 权限失败 ↔ 死锁 之间游走）→ 整跑结果无法复现，
    也没法判断「这次失败算不算我的」。

本脚本用**另一个库名**跑整跑 → 与共享库零交集 → 结果可复现。

用法：
    python scripts_run_isolated_tests.py --db-name ats_test_iso -- -q -m "not quarantine"
    python scripts_run_isolated_tests.py --db-name ats_test_iso --precheck-only

注意（本地 MySQL 权限）：
    普通开发账号（如 ats_dev）通常**没有** root，无法给自己授权。
    本地已有的、已授权可直接用的库（实测有全权限）：
        ats_test / test_ats_test / ats_t03_ci / test_ats_t03_ci
        ats_drift_repro / ats_0030_probe
    用新库名时，脚本会打印出需要 DBA 执行的授权 SQL。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

# 本地已授权、可直接使用的候选库（按优先级）
KNOWN_GRANTED = ('ats_t03_ci', 'ats_drift_repro', 'ats_0030_probe', 'ats_test')


def _db_settings() -> dict:
    """从 Django settings 里取连接参数（读 .env 的逻辑由 settings 负责）。"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
    sys.path.insert(0, str(BASE))
    import django

    django.setup()
    from django.conf import settings

    cfg = settings.DATABASES['default']
    return {
        'host': cfg.get('HOST') or '127.0.0.1',
        'port': int(cfg.get('PORT') or 3306),
        'user': cfg.get('USER') or '',
        'password': cfg.get('PASSWORD') or '',
        'name': cfg.get('NAME') or '',
    }


def precheck(db_name: str) -> tuple[bool, str]:
    """检查目标库是否可用；返回 (是否可用, 说明)。"""
    try:
        import pymysql
    except ImportError:
        return False, '缺少 pymysql 依赖'

    cfg = _db_settings()
    target = f'test_{db_name}'
    try:
        conn = pymysql.connect(
            host=cfg['host'],
            port=cfg['port'],
            user=cfg['user'],
            password=cfg['password'],
            database=target,
            connect_timeout=5,
        )
    except Exception as exc:
        return False, (
            f'连不上测试库 {target}：{type(exc).__name__}: {exc}\n'
            f'    若该库不存在，需要 DBA 执行：\n'
            f'      CREATE DATABASE `{target}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n'
            f'      GRANT ALL PRIVILEGES ON `{target}`.* TO \'{cfg["user"]}\'@\'%\';'
        )

    try:
        with conn.cursor() as cur:
            cur.execute('SHOW GRANTS FOR CURRENT_USER')
            grants = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

    has_all = any(f'`{target}`' in g and 'ALL PRIVILEGES' in g.upper() for g in grants)
    if not has_all:
        return False, (
            f'账号 {cfg["user"]} 对 {target} 没有全权限（迁移需要 ALTER）\n'
            f'    需要 DBA 执行：GRANT ALL PRIVILEGES ON `{target}`.* TO \'{cfg["user"]}\'@\'%\';\n'
            f'    当前授权：{grants}'
        )
    return True, f'{target} 可用（账号 {cfg["user"]} 拥有全权限）'


def main() -> int:
    parser = argparse.ArgumentParser(
        description='用独立测试库跑 pytest（隔离共享库的并发干扰）',
        epilog='例：python scripts_run_isolated_tests.py --db-name ats_t03_ci -- -q',
    )
    parser.add_argument(
        '--db-name',
        default=os.environ.get('ATS_TEST_DB_NAME', 'ats_t03_ci'),
        help='独立库的库名（测试库名会自动加 test_ 前缀）；也可用环境变量 ATS_TEST_DB_NAME',
    )
    parser.add_argument(
        '--precheck-only',
        action='store_true',
        help='只做权限/连通性检查，不跑测试',
    )
    parser.add_argument(
        'pytest_args',
        nargs='*',
        help='传给 pytest 的参数（放在 -- 之后）',
    )
    args = parser.parse_args()

    ok, message = precheck(args.db_name)
    print(f'[precheck] {message}')
    if not ok:
        print('\n可用候选（本地已授权）：' + ', '.join(KNOWN_GRANTED))
        return 2
    if args.precheck_only:
        return 0

    env = dict(os.environ)
    env['DB_NAME'] = args.db_name
    env.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
    cmd = [sys.executable, '-m', 'pytest', *args.pytest_args]
    print(f'[run] DB_NAME={args.db_name}  →  {" ".join(cmd)}\n')
    return subprocess.call(cmd, cwd=str(BASE), env=env)


if __name__ == '__main__':
    sys.exit(main())
