"""P1-2 第十一批审计式测试: 验证 candidate 模块所有 noqa: BLE001 都具备明确意图注释 + 1 处真窄化范式。

策略: candidate 是"候选人管理 + signal 兜底审计"模块, 5 处 except Exception 全是设计内"宽捕获":
  - signals.py post_save 兜底审计 2 处 (noqa 化)
  - services.py 并发 upsert by phone 真窄化 (OperationalError, IntegrityError)
  - views.py 批量创建单条失败 (noqa 化)
  - views.py Talent pool 同步失败 (noqa 化)

未来 PR 想在 candidate 加新 except Exception 但忘标 noqa 或忘写意图 → 测试红.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


CAND_DIR = Path('apps/candidate')


def _collect_blind_excepts(root: Path) -> list[tuple[str, int, str]]:
    out = []
    for py in root.rglob('*.py'):
        if '__pycache__' in py.parts or 'migrations' in py.parts or 'tests' in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if n.type and ast.unparse(n.type) == 'Exception':
                src = py.read_text(encoding='utf-8').splitlines()
                line_text = src[n.lineno - 1] if n.lineno - 1 < len(src) else ''
                out.append((str(py), n.lineno, line_text))
    return out


def _collect_narrow_excepts(root: Path) -> list[tuple[str, int, str, str]]:
    """返回 (path, lineno, line_text, narrow_set_str) - 真窄化的非 Exception except."""
    out = []
    for py in root.rglob('*.py'):
        if '__pycache__' in py.parts or 'migrations' in py.parts or 'tests' in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if n.type and ast.unparse(n.type) != 'Exception':
                src = py.read_text(encoding='utf-8').splitlines()
                line_text = src[n.lineno - 1] if n.lineno - 1 < len(src) else ''
                out.append((str(py), n.lineno, line_text, ast.unparse(n.type)))
    return out


def test_all_candidate_blind_excepts_have_noqa_with_intent() -> None:
    """candidate 模块所有 except Exception 必须:
       1. 同行或上一行有 # noqa: BLE001 标记
       2. noqa 后必须跟 ≥5 字符的意图说明
    """
    issues = []
    for path, lineno, line_text in _collect_blind_excepts(CAND_DIR):
        m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
        if not m_noqa:
            issues.append(f'{path}:{lineno} 缺少 # noqa: BLE001 标记')
            continue
        intent = m_noqa.group(1).strip()
        if len(intent) < 5:
            issues.append(
                f'{path}:{lineno} noqa 意图说明不足 (>{len(intent)}<, 需 ≥5 字符)'
            )
    assert not issues, 'candidate noqa 审计失败:\n' + '\n'.join(issues)


def test_candidate_narrow_set_actually_works() -> None:
    """services.py 真窄化: except (OperationalError, IntegrityError) - ORM 并发冲突.

    验证属性:
      1. 窄集异常被捕获 (logger.warning 调用 + 重 fetch)
      2. AttributeError (编程错误) 不再被吞, 向上抛
    """
    narrow = _collect_narrow_excepts(CAND_DIR)
    found_orm_narrow = False
    for path, lineno, _line, narrow_set in narrow:
        if 'OperationalError' in narrow_set and 'IntegrityError' in narrow_set:
            found_orm_narrow = True
            assert 'Exception' not in narrow_set.split(','), \
                f'{path}:{lineno} 应窄集而非 Exception'
    assert found_orm_narrow, 'candidate 找不到 ORM 窄集真窄化'


# ============================================================
# 范式案例: CandidateService upsert by phone 并发冲突
# ============================================================

@pytest.mark.django_db
def test_upsert_by_phone_retry_on_integrity_error(monkeypatch):
    """get_or_create_by_phone 在 IntegrityError 冲突时重 fetch 现有候选.

    这是 services.py 真窄化的核心契约: 并发场景 ORM 唯一键冲突后应返已存在记录.
    """
    from apps.candidate.models import Candidate
    from apps.candidate.services import CandidateService
    from django.db import IntegrityError

    # 先建一个 phone 已存在的候选
    existing = Candidate.objects.create(
        phone='13800000000', name='Existing', email='e@test.com',
    )

    # 让 CandidateService.create_candidate 抛 IntegrityError (mock 并发冲突)
    def buggy_create(*args, **kwargs):
        raise IntegrityError('mocked concurrent insert conflict')

    monkeypatch.setattr(CandidateService, 'create_candidate', staticmethod(buggy_create))

    # get_or_create_by_phone 应捕获 IntegrityError, 重 fetch, 返 existing
    result = CandidateService.get_or_create_by_phone(
        phone='13800000000',
        defaults={'name': 'New', 'email': 'n@test.com'},
        actor=None,
    )
    assert result.id == existing.id, '应返重 fetch 的 existing 候选'


@pytest.mark.django_db
def test_upsert_by_phone_attribute_error_no_longer_swallowed(monkeypatch):
    """get_or_create_by_phone 在 AttributeError (编程错误) 不再被吞, 向上抛."""
    from apps.candidate.services import CandidateService

    def buggy_create(*args, **kwargs):
        raise AttributeError('mocked typo in create_candidate')

    monkeypatch.setattr(CandidateService, 'create_candidate', staticmethod(buggy_create))

    with pytest.raises(AttributeError, match='mocked typo'):
        CandidateService.get_or_create_by_phone(
            phone='13800000001',
            defaults={'name': 'New', 'email': 'n@test.com'},
            actor=None,
        )