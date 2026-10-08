"""扫描代码库中的技术债注释 (TODO / FIXME / HACK / XXX), 强制「带可追溯编号」规范.

用法:
    python scripts_scan_todo.py                 # 报告模式, 永不阻断 (CI 现状)
    python scripts_scan_todo.py --strict        # 发现不合规标记即 exit 1, 用于存量清理后翻严格门禁
    python scripts_scan_todo.py --root apps config

规范 (#43, 2026-10-09):
    技术债注释 MUST 携带可追溯编号, 形如:
        TODO(#123): 描述
        FIXME(ATS-456): 描述
        HACK(#789): 描述
    未带编号的裸标记 (如 `TODO: 以后重构`) 视为不合规 —— 没有 issue 链接的技术债
    等于永久没人跟, 正是审计 CODE_REVIEW 指出的「TODO/FIXME 散落、不可审计」问题。

设计: 当前默认报告模式 (exit 0), 直接挂 CI 不会打断现有流水线; 待存量裸标记
    补完编号后, 把 CI 这一步加 `--strict` 即翻成硬门禁 (与 #27 ruff 门禁同源思路:
    只许减少、不许新增)。
"""
import os
import re
import sys

# 扫描的后缀
SCAN_SUFFIXES = ('.py', '.ts', '.tsx', '.js', '.jsx', '.vue')

# 技术债标记
MARKER = re.compile(
    r'\b(TODO|FIXME|HACK|XXX)\b\s*(?:\(([^)]*)\))?\s*[:\-]?\s*(.*?)\s*$'
)

# 合法编号: #123 或 ATS-456 这类 issue/ticket 引用
ISSUE_REF = re.compile(r'#\d+|\b[A-Z]{2,}-\d+\b')


def iter_source_lines(root):
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过常见非源码目录
        dirnames[:] = [
            d for d in dirnames
            if d not in ('.venv', 'venv', 'node_modules', '__pycache__',
                         '.git', 'migrations', 'static', 'media')
        ]
        for fn in filenames:
            if not fn.endswith(SCAN_SUFFIXES):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    for i, line in enumerate(fh, 1):
                        yield path, i, line.rstrip('\n')
            except (OSError, UnicodeDecodeError):
                continue


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    roots = ['apps', 'config']
    strict = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--strict':
            strict = True
        elif a == '--root':
            i += 1
            roots = [argv[i]]
        elif a.startswith('--root='):
            roots = [a.split('=', 1)[1]]
        else:
            roots = [a]
        i += 1

    base = os.path.dirname(os.path.abspath(__file__))
    roots = [r if os.path.isabs(r) else os.path.join(base, r) for r in roots]

    total = 0
    violations = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for path, lineno, text in iter_source_lines(root):
            m = MARKER.search(text)
            if not m:
                continue
            total += 1
            ref = m.group(2)
            if ref and ISSUE_REF.search(ref):
                continue  # 带编号, 合规
            rel = os.path.relpath(path, base)
            violations.append((rel, lineno, m.group(1), m.group(3).strip()[:60]))

    print(f'技术债注释扫描 (roots={roots}):')
    print(f'  标记总数      : {total}')
    print(f'  合规(带编号) : {total - len(violations)}')
    print(f'  不合规(裸标记): {len(violations)}')
    if violations:
        print('\n不合规清单 (须补 #issue 或 ticket 编号):')
        for rel, lineno, tag, snippet in sorted(violations):
            print(f'  {rel}:{lineno}  {tag}  {snippet}')

    # 默认报告模式不阻断; --strict 才把不合规变成失败 (存量清理后启用)
    if strict and violations:
        print('\n[strict] 存在不合规技术债注释, 退出 1')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
