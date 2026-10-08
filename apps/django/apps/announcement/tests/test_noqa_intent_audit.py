"""P1-2 第十批审计式测试: 验证 announcement 模块所有 noqa: BLE001 都具备明确意图注释。

策略: announcement 是"公告/附件/通知"模块, 5 处 except Exception 全是设计内"宽捕获":
  - models.py/serializers.py 读 file.url 失败 (Storage 不可用返空串)
  - views.py 物理文件删除失败 (best-effort, DB 软删仍生效)
  - views.py 单用户发送/提醒失败 (批处理, 单用户失败不影响其他)

未来 PR 想在 announcement 加新 except Exception 但忘标 noqa 或忘写意图 → 测试红.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

ANN_DIR = Path('apps/announcement')


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


def test_all_announcement_blind_excepts_have_noqa_with_intent() -> None:
    """announcement 模块所有 except Exception 必须:
       1. 同行或上一行有 # noqa: BLE001 标记
       2. noqa 后必须跟 ≥5 字符的意图说明
    """
    issues = []
    for path, lineno, line_text in _collect_blind_excepts(ANN_DIR):
        m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
        if not m_noqa:
            issues.append(f'{path}:{lineno} 缺少 # noqa: BLE001 标记')
            continue
        intent = m_noqa.group(1).strip()
        if len(intent) < 5:
            issues.append(
                f'{path}:{lineno} noqa 意图说明不足 (>{len(intent)}<, 需 ≥5 字符)'
            )
    assert not issues, 'announcement noqa 审计失败:\n' + '\n'.join(issues)


def test_announcement_module_count_consistent_with_baseline() -> None:
    """announcement 模块所有 except Exception 必须都被 noqa 化."""
    unmarked = []
    for path, lineno, line_text in _collect_blind_excepts(ANN_DIR):
        if '# noqa: BLE001' not in line_text:
            unmarked.append((path, lineno))
    assert not unmarked, (
        f'announcement 出现 {len(unmarked)} 处未 noqa 化的盲 except:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unmarked)
    )


# ============================================================
# 范式案例: file_url 兜底
# ============================================================

@pytest.mark.django_db
def test_announcement_file_url_returns_empty_on_storage_failure():
    """Attachment.file_url 在 file.url 抛异常时返空串, 不应让 property 500.

    这是 announcement noqa 的核心契约: 模型 property 不能因为 storage 不可用让序列化/视图 500.
    """
    from unittest.mock import PropertyMock, patch

    from apps.announcement.models import AnnouncementAttachment

    # 构造 Attachment 实例 (无真实文件), 让 file.url 抛异常
    att = AnnouncementAttachment()
    att.file = None  # no file attached → property 应直接返 ''
    assert att.file_url == ''

    # 模拟 file 存在但 file.url 抛异常
    fake_file = MagicMock()
    type(fake_file).url = PropertyMock(side_effect=OSError('mocked storage unavailable'))
    att.file = fake_file
    assert att.file_url == ''