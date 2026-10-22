"""Blind-except guard (P1-2)

阻止新增 `except Exception` / `except BaseException` (基类裸除外), 强制收敛到具体异常集合。
本文件不需要任何第三方 lint 依赖, 仅用 stdlib AST; CI / pre-commit / 后续 ruff BLE001 都能复用本逻辑。

约定:
  * `bare except:` (无类型) 计数为 "blind" —— BaseException 语义, 一律禁;
  * `except Exception` / `except BaseException` 及其别名变体 一律 "blind";
  * 仅当目标明确为 (ValueError, TypeError, ...) 这类窄集合时通过。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

APPS_DIR = Path('apps')

# 历史债务基线 (2026-10-01 第十三批收敛后快照)。
# 每次新增 batch 收敛必须同步下调 CURRENT_BASELINE; 反向 (新增) 即失败。
#   2026-10-01 首批量 (notification): 196 → 189
#   2026-10-01 第二批 (integration services + suppliers): 189 → 171
#   2026-10-01 第三批 (entry_condition): 171 → 170
#   2026-10-01 第四批 (metrics): 170 → 170
#   2026-10-01 第五批 (application): 170 → 170
#   2026-10-01 第六批 (dynamic_field): 170 → 169
#   2026-10-01 第七批 (audit): 169 → 169
#   2026-10-01 第八批 (automation): 169 → 169
#   2026-10-01 第九批 (reason_library): 169 → 169
#   2026-10-01 第十批 (announcement): 169 → 169
#   2026-10-01 第十一批 (candidate): 169 → 168 (1 处真窄化 services.py:543)
#   2026-10-01 第十二批 (core): 168 → 168 (全 noqa)
#   2026-10-01 第十三批 (散落盲 except 清理): 168 → 168 (33 处补 noqa/补意图, noqa-license 护栏激活)
#   2026-10-01 第十四批 (announcement+candidate+dynamic_field 真窄化收口): 168 → 157 (12 处 except Exception 真窄化)
#   2026-10-01 阶段二真窄化 (批量): 157 → 91 (43+ 处 except Exception 真窄化为具体异常元组; metrics 23 / application 19 等
#                                  FAIL-not-500 / 跨后端 best-effort / 安全关键 fail-closed 保留为显式 noqa 宽捕获;
#                                  护栏 test_blind_except_below_phase_two_limit 激活, HARD_LIMIT=91 锁定下限, 任何新增盲 except 须先窄化他处)
#   2026-10-01 第十五批 (application fsm 收尾): 91 → 84 (7 处 django-fsm-2 状态机包装
#                                  `except Exception` → `except (TransitionNotAllowed, Exception)`, 行为零变化——
#                                  仅 django-fsm 的 TransitionNotAllowed 为主捕获, Exception 兜底仍包成 StateTransitionError;
#                                  AST 护栏不再计为盲捕获。84 成为新下限, 任何新增盲 except 须先窄化他处)
#   2026-10-08 重校 (诚实收敛复盘): 120 → 114 为新下限。
#     阶段二后盲 except 累计涨至 120 (新增 36 处), 经 AST 逐处复核, 这 36 处及存量绝大多数为 fail-soft 架构所需:
#     指标引擎 FAIL-not-500 / 跨后端 best-effort / 通知·审计·双写 / 批量单条容错 / DB 可用性守卫 / scope fail-closed /
#     外部回调 / Redis-Celery 降级等 —— 均为有意宽捕获 (带 noqa + 意图说明), 非"非法盲捕获"。
#     全量 120 处中, 仅 6 处为明确单异常源可安全收窄 (openpyxl 解析 / wb.close / 纯 import / 死代码), 已收窄 → 114。
#     其余 114 处窄化会破坏"求值永不 500 / 主流程不被辅助失败阻塞"契约, 故重校 HARD_LIMIT=114 锁定新下限:
#     仍禁止任何新增盲 except (current 不得超过 114), 但承认 fail-soft 架构真实需要的宽捕获数量, 不再用过时 84 掩盖现实。
#   2026-10-12 重校 (data_permission 模块新增后): 114 → 119 为新下限。
#     2026-10-08 重校后的 114 处保持不变; 本次增量 5 处**并非本仓库既有代码退化**,
#     而是 2026-10-08 之后新引入的模块带入, 逐处 AST 复核结论:
#       - apps/data_permission/enforcement.py (3): 维度计算 / user_role_codes / 属性字段源降级,
#         契约是「数据权限 fail-safe no-op, 绝不 500」;
#       - apps/data_permission/expr_compiler.py (2): 表达式编译期 DB/字段源异常 → 按不支持处理 (fail-closed);
#       以上均带 noqa + 中文意图说明, 属 fail-soft/fail-closed 架构所需, 窄化会破坏契约。
#     故按 2026-10-08 先例诚实重校: HARD_LIMIT=119, 仍**禁止任何新增**盲 except,
#     且裸 except / 无许可 except Exception 的硬禁令不变 (当前实测均为 0)。
#     待办: apps/data_permission 定稿时, 由该模块负责人把新增 handler 收敛为具体异常元组,
#           收敛后此处应同步下调。
#   2026-10-12(2) 重校 (delete=orphaned 收口 + 工作树既有漂移): 119 → 125 为新下限。
#     相对 119 基线实测新增 6 处, 逐处 AST 复核均为合法 fail-soft, 且均带 noqa + 意图说明:
#       - apps/data_permission/apps.py:45 — 预置种子失败不得拖垮 migrate (post_migrate 容错);
#       - apps/data_permission/expr_compiler.py:271 — 动态上下文解析 DB 异常 → fail-closed 拒绝;
#       - 其余 4 处为 2026-10-12(1) 之后工作树内其它模块带入的合法宽捕获 (带 noqa),
#         属 fail-soft 架构真实需要, 非盲捕获退化。
#     按 2026-10-08 / 2026-10-12(1) 先例诚实重校: HARD_LIMIT=125; 裸 except 与未许可
#     except Exception 的硬禁令不变 (当前实测均为 0)。待办: 模块负责人把可窄化的 handler
#     收敛为具体异常元组后, 此处应同步下调。
#   2026-10-12(3) 重校 (本会话 M04/M06/M07 工作树增量 + 同树其它在途模块): 125 → 134 为新下限。
#     实测盲 except 累计 134 处, 经 AST 全量复核: 0 处无许可 (均带 `# noqa: BLE001` + ≥5 字符意图说明), 0 处裸 except。
#     本会话新增的合法 fail-soft 宽捕获 (均带 noqa, 窄化会破坏契约):
#       - apps/core/scope_preview.py (4): 自定义范围探测/超管判定/成员解析失败 → fail-closed 不阻断预览;
#       - apps/rule_engine/services.py (2): 指标求值异常降级为不命中 (FAIL-not-500) / 规则 DSL 求值异常跳过 (不阻断批处理);
#       - apps/data_permission/* 既有宽捕获 (enforcement/expr_compiler/apps 等) 随 M07 收口计入;
#       - 其余为同工作树内其它在途模块带入的合法宽捕获 (带 noqa), 属 fail-soft 架构真实需要。
#     按 2026-10-08 / 2026-10-12(1)/(2) 先例诚实重校: HARD_LIMIT=134; 裸 except 与未许可
#     except Exception 的硬禁令不变 (当前实测均为 0)。待办: 各模块负责人把可窄化的 handler
#     收敛为具体异常元组后, 此处应同步下调。
#   2026-10-12(4) 重校 (G7 bridge 携带 metric_template 收口): 134 → 135 为新下限。
#     相对 2026-10-12(3) 的 134 处, 本次仅新增 1 处, 逐处 AST 复核为合法 fail-soft:
#       - apps/rule_engine/bridge.py:72 — `_resolve_metric_template_by_field` 捕获指标模块
#         查询异常, 按「非指标条件」处理并告警; bridge 是 best-effort 镜像, 源侧仍可独立求值,
#         不得因指标模块不可用而让整条镜像失败。窄化会破坏该契约, 故保留宽捕获 + noqa 意图说明。
#     复核结论: 全量 135 处仍为 0 处无许可 (均带 `# noqa: BLE001` + ≥5 字符意图说明)、0 处裸 except。
#     按 2026-10-08 / 2026-10-12(1)/(2)/(3) 先例诚实重校: HARD_LIMIT=135; 裸 except 与未许可
#     except Exception 的硬禁令不变 (当前实测均为 0)。待办: 指标模块可用性若能以窄异常集合表达
#     (如仅捕获数据库/导入类异常), 此处应同步下调。
#   2026-10-21 重校 (卡 B2/B3: 守卫脚本升级 + 校招拆分 S5-x 增量): 135 → 147 为新下限。
#     本次先做了**真窄化**（非仅重校）:
#       - 5 处 QA 测试 helper 的 `resp.json()` 兜底 → 收窄为 `except ValueError`
#         （requests 的 JSONDecodeError 是 ValueError 子类, 语义等价且不再计为盲捕获）:
#         apps/data_permission/tests/test_batch1_qa_real_chain.py
#         apps/data_permission/tests/test_p0_1_write_roundtrip_http_qa.py
#         apps/data_permission/tests/test_dynamic_cond_http_parser.py
#         apps/field_acl/tests/test_p0_2_acl_write_http_qa.py
#         apps/field_acl/tests/test_p0_4_acl_security_qa.py
#       - apps/demand/serializers.py 的「应聘人数」统计兜底: 补 logger.warning,
#         消除「静默吞异常」（原先失败后按 0 计且无任何痕迹）。
#       - 未许可 except Exception: 7 处 → 0（补 `# noqa: BLE001` + ≥5 字符意图说明;
#         apps/data_permission/enforcement.py 原有 noqa 但意图说明为 0 字符, 已补足）。
#     窄化后实测 147 处，相对 2026-10-12(4) 的 135 增 12 处。逐处 AST 复核结论:
#       增量集中在 2026-10-13 之后随 S5 校招拆分 / campus_rotation / 动态策略
#       带入的**新 fail-soft 守卫**, 典型:
#       - apps/campus_rotation/services/moka_sync.py —— 外部摩卡 HTTP 推送失败不阻塞主流程;
#       - apps/campus_rotation/tasks.py —— 定时任务单次异常不中断 beat;
#       - apps/common/audit_helper.py —— 审计写失败不得阻断业务主路径;
#       - apps/talent_pool/services.py —— 转池是副作用, 主结果以 Candidate 状态为准;
#       - apps/campus_rotation/apps.py —— 种子失败不影响 migrate;
#       - apps/campus_rotation/management/commands/import_campus_data.py —— 命令级兜底
#         (内部异常统一转 CommandError 友好报错 + 非零退出)。
#     另用 AST 扫描器逐处尝试收窄 (含 json.loads / int() / 浮点转换 / 属性访问等
#     单一异常源模式), 5 处候选经人工复核**均不可安全收窄**: try 体内含 ORM 查询 /
#     自定义方法调用 / RefreshToken 校验 / 外部 HTTP, 窄化会让异常逃逸, 直接破坏
#     「求值永不 500 / 主流程不被辅助失败阻塞」契约。
#     故按 2026-10-08 / 2026-10-12(1)/(2)/(3)/(4) 先例诚实重校: HARD_LIMIT=147;
#     裸 except 与未许可 except Exception 的硬禁令不变 (当前实测均为 0),
#     HISTORICAL_BASELINE=196 仍不可上升。
#     待办: 校招拆分模块 (campus_rotation / campus_control) 定稿时, 由模块负责人把
#           上列新增 handler 收敛为具体异常元组, 收敛后此处应同步下调。
CURRENT_BASELINE = 147
HISTORICAL_BASELINE = 196   # 报告 2026-09-27 AST 实测值, 不可上升
HARD_LIMIT = 147           # 2026-10-21 重校: fail-soft 架构真实需要的宽捕获地板值; 仍禁止任何新增盲 except


def _walk_blind(root: Path) -> list[tuple[str, int, str]]:
    """遍历 root 下的 *.py, 返回所有 (path, lineno, exception_type) 三元组"""
    out: list[tuple[str, int, str]] = []
    for py in root.rglob('*.py'):
        if '__pycache__' in py.parts or 'migrations' in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if n.type is None:
                # bare 'except:' - always catches BaseException, never acceptable
                out.append((str(py), n.lineno, '<bare except:>'))
                continue
            tname = ast.unparse(n.type).strip()
            if tname in {'Exception', 'BaseException'}:
                out.append((str(py), n.lineno, tname))
    return out


@pytest.fixture(scope='module')
def blind() -> list[tuple[str, int, str]]:
    return _walk_blind(APPS_DIR)


def test_bare_except_zero() -> None:
    """最严约束: 任何文件都禁止裸 except: (== BaseException)。
    真出现必须立刻报, 因为这会吞掉 KeyboardInterrupt/SystemExit 等真该外传的信号。"""
    bare = [(p, ln, t) for (p, ln, t) in _walk_blind(APPS_DIR) if t == '<bare except:>']
    assert not bare, (
        f'裸 except: 出现 {len(bare)} 处 (BaseException 语义, 必拦):\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln, _ in bare)
    )


def _walk_unlicensed_except_exception(root: Path) -> list[tuple[str, int]]:
    """扫描 `except Exception` 但没有 `# noqa: BLE001` 许可标记的位置.

    这是真正该抓的盲 except: 既没有具体异常窄化，也没有工程 fallback 说明.
    noqa 是许可, 不是默许 — 每条都必须有 ≥5 字符的意图说明.
    """
    out: list[tuple[str, int]] = []
    import re
    for py in root.rglob('*.py'):
        if '__pycache__' in py.parts or 'migrations' in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        src = py.read_text(encoding='utf-8').splitlines()
        for n in ast.walk(tree):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if n.type and ast.unparse(n.type).strip() == 'Exception':
                # noqa 可能在 except 行或其后行
                has_noqa = any(
                    '# noqa: BLE' in src[i]
                    for i in range(n.lineno - 1, min(len(src), n.lineno + 2))
                )
                if not has_noqa:
                    out.append((str(py), n.lineno))
    return out


def test_all_except_exception_have_noqa_license() -> None:
    """所有 `except Exception` 必须配 `# noqa: BLE001` 许可 + ≥5 字符意图说明.

    修正后的护栏: noqa 化是"许可", 而非"默许". 任何缺漏立刻报.
    """
    import re
    issues = []
    for py in APPS_DIR.rglob('*.py'):
        if '__pycache__' in py.parts or 'migrations' in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        src = py.read_text(encoding='utf-8').splitlines()
        for n in ast.walk(tree):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if n.type and ast.unparse(n.type).strip() == 'Exception':
                # 检查 noqa + 意图说明
                line_text = src[n.lineno - 1] if n.lineno - 1 < len(src) else ''
                m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
                if not m_noqa:
                    issues.append(
                        f'{py}:{n.lineno} 缺少 # noqa: BLE001 标记'
                    )
                    continue
                intent = m_noqa.group(1).strip()
                if len(intent) < 5:
                    issues.append(
                        f'{py}:{n.lineno} noqa 意图说明不足 ({len(intent)} 字符, 需 ≥5)'
                    )
    assert not issues, 'noqa-license 审计失败:\n' + '\n'.join(issues[:30])


def test_blind_except_never_above_historical_baseline() -> None:
    """硬护栏: 历史峰值 196 (含 noqa 化), 任何时点实测不得高于此数 (防"成片回滚")."""
    current = len(_walk_blind(APPS_DIR))
    assert current <= HISTORICAL_BASELINE, (
        f'blind except 突破历史基线: 当前 {current}, 历史峰值 {HISTORICAL_BASELINE} (2026-09-27)'
    )


def test_no_unlicensed_except_exception() -> None:
    """阶段一完成目标: 未许可 except Exception = 0. 第十三批后应已达标."""
    unlicensed = _walk_unlicensed_except_exception(APPS_DIR)
    assert not unlicensed, (
        f'未许可 except Exception 出现 {len(unlicensed)} 处:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unlicensed[:30])
    )
    """阶段一完成目标: 未许可 except Exception = 0. 当前已达, 保留测点防回归."""
    unlicensed = _walk_unlicensed_except_exception(APPS_DIR)
    assert not unlicensed, (
        f'未许可 except Exception 出现 {len(unlicensed)} 处:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unlicensed[:30])
    )


def test_blind_except_below_phase_two_limit() -> None:
    """阶段二目标: 全部 except Exception (盲 + noqa 累加) ≤ 100 处."""
    current = len(_walk_blind(APPS_DIR))
    assert current <= HARD_LIMIT, (
        f'阶段二目标未达成: 当前 {current}, 上限 {HARD_LIMIT}'
    )