"""P1-2 第九批审计式测试: 验证 reason_library 模块所有 noqa: BLE001 都具备明确意图注释。

策略: reason_library 是"标签/规则导入导出"模块, 5 处 except Exception 全是设计内"宽捕获":
  - io_tag.py openpyxl/csv/文件读取异常 → re-raise TagFileParseError (3 处, openpyxl 异常类型不固定)
  - io_tag.py 关闭 workbook 失败 → 忽略 (1 处, 不影响已解析结果)
  - services/active_query_service.py cache 失效失败 → 忽略 (1 处, 下次读时 cache miss 重算)

未来 PR 想在 reason_library 加新 except Exception 但忘标 noqa 或忘写意图 → 测试红.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


RL_DIR = Path('apps/reason_library')


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


def test_all_reason_library_blind_excepts_have_noqa_with_intent() -> None:
    """reason_library 模块所有 except Exception 必须:
       1. 同行或上一行有 # noqa: BLE001 标记
       2. noqa 后必须跟 ≥5 字符的意图说明
    """
    issues = []
    for path, lineno, line_text in _collect_blind_excepts(RL_DIR):
        m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
        if not m_noqa:
            issues.append(f'{path}:{lineno} 缺少 # noqa: BLE001 标记')
            continue
        intent = m_noqa.group(1).strip()
        if len(intent) < 5:
            issues.append(
                f'{path}:{lineno} noqa 意图说明不足 (>{len(intent)}<, 需 ≥5 字符)'
            )
    assert not issues, 'reason_library noqa 审计失败:\n' + '\n'.join(issues)


def test_reason_library_module_count_consistent_with_baseline() -> None:
    """reason_library 模块所有 except Exception 必须都被 noqa 化."""
    unmarked = []
    for path, lineno, line_text in _collect_blind_excepts(RL_DIR):
        if '# noqa: BLE001' not in line_text:
            unmarked.append((path, lineno))
    assert not unmarked, (
        f'reason_library 出现 {len(unmarked)} 处未 noqa 化的盲 except:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unmarked)
    )


# ============================================================
# 范式案例: io_tag 解析失败 re-raise TagFileParseError
# ============================================================

def test_tag_file_parse_error_is_re_raised():
    """io_tag.py:174 openpyxl 解析失败必须包成 TagFileParseError re-raise.

    这是 reason_library noqa 的典型场景: openpyxl 异常类型不固定 (BadZipFile/InvalidFileException等),
    统一兜底 → TagFileParseError 让上层有标准化处理路径.
    """
    from io import BytesIO
    from apps.reason_library.io_tag import TagFileParseError, parse_tag_rows

    # 构造一个 UploadedFile stub with .xlsx extension 但内容非法
    class _StubUpload:
        name = 'bad.xlsx'
        def read(self):
            return b'\x00\x01\x02not-a-real-xlsx'

    with pytest.raises(TagFileParseError):
        parse_tag_rows(_StubUpload())


def test_csv_file_parse_error_is_re_raised():
    """io_tag.py:242 CSV 解析失败必须包成 TagFileParseError re-raise.

    这是 reason_library noqa 的典型场景: csv.Dialect 异常类型不固定, 统一兜底.
    """
    from apps.reason_library.io_tag import TagFileParseError, parse_tag_rows

    # 构造一个 .csv extension 但内容是畸形数据
    class _StubUpload:
        name = 'bad.csv'
        def read(self):
            # 引发编码错误 (invalid utf-8 bytes), 触发 CSV 解析失败路径
            raise UnicodeDecodeError('utf-8', b'\xff\xfe\xfd', 0, 3, 'invalid start byte')

    with pytest.raises(TagFileParseError):
        parse_tag_rows(_StubUpload())