"""守卫：测试文件不得使用**模块级** ``pytest.mark.django_db(transaction=True)``。

与 CI 的 ``scripts_scan_module_level_transaction.py --strict`` 同源，
这里再跑一次是为了让**本地整跑**也能拦住（CI 之外的回归也能被看到）。

为什么是阻断级：模块级事务标记会让该文件**每个**用例在 teardown 都
``flush`` 整库 → 抹掉已提交种子 → 字典序在后的用例批量 403
（2026-10-21 整跑 flaky 根因之一，详见
``docs/07-audit/C4_手机号邮箱落库加密_2026-10-21.md`` §5）。
"""
import importlib.util
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent


def _load_scanner():
    """按文件路径加载扫描器脚本（它是脚本，不是包内模块）。"""
    path = BASE / 'scripts_scan_module_level_transaction.py'
    spec = importlib.util.spec_from_file_location('scan_module_level_transaction', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def scanner():
    return _load_scanner()


def test_no_module_level_transaction_markers(scanner):
    findings = scanner.find_module_level_transactional_markers()
    assert not findings, (
        '发现模块级 django_db(transaction=True)（每个用例 teardown 都会 flush 整库，'
        '抹掉已提交种子 → 后续用例批量 403）：\n'
        + '\n'.join(f'  · {rel}:{line}' for rel, line, _ in findings)
    )


def test_scanner_detects_a_synthetic_violation(tmp_path, scanner, monkeypatch):
    """守卫本身要有效：造一个违规文件，扫描器必须能抓到。"""
    bad = tmp_path / 'test_synthetic_violation.py'
    bad.write_text(
        'import pytest\n\npytestmark = pytest.mark.django_db(transaction=True)\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(scanner, 'SEARCH_ROOTS', (str(tmp_path),))

    findings = scanner.find_module_level_transactional_markers()
    assert len(findings) == 1, '扫描器必须能抓到模块级事务标记'
    rel, line, _reason = findings[0]
    assert 'test_synthetic_violation.py' in rel
    assert line > 0


def test_scanner_ignores_method_level_markers(tmp_path, scanner, monkeypatch):
    """方法级装饰器是**允许**的（只影响那一个用例）。"""
    good = tmp_path / 'test_method_level_ok.py'
    good.write_text(
        'import pytest\n\n\n'
        '@pytest.mark.django_db(transaction=True)\n'
        'def test_one():\n    assert True\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(scanner, 'SEARCH_ROOTS', (str(tmp_path),))

    assert scanner.find_module_level_transactional_markers() == []


def test_scanner_ignores_plain_django_db(tmp_path, scanner, monkeypatch):
    """普通 ``django_db``（非事务）不算违规。"""
    ok = tmp_path / 'test_plain_db_ok.py'
    ok.write_text(
        'import pytest\n\npytestmark = pytest.mark.django_db\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(scanner, 'SEARCH_ROOTS', (str(tmp_path),))

    assert scanner.find_module_level_transactional_markers() == []


def test_known_exceptions_are_documented(scanner):
    """已登记的历史例外必须写明理由（否则「例外」会变成「盲区」）。"""
    for rel, reason in scanner.KNOWN_EXCEPTIONS.items():
        assert reason.strip(), f'{rel} 的例外理由不能为空'
