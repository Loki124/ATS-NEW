# Phase 2 开工前预检盘点（429 期间人工完成）

> 本文档由主理人齐活林在 2026-08-03 16:13-17:13 期间完成。
> 起因：所有 agent 在同一时刻触发 HTTP 429 频率限制（software-architect /
> software-engineer / software-qa-engineer-2 / software-qa-engineer-4），
> Phase 2 设计增补被迫中断。本盘点由主理人用本地工具手工完成，
> 明天 agent 恢复后可作为设计增补的输入素材。

---

## 一、被 `pytest.mark.skip` 静默禁用的测试 ——「假绿」最纯粹的标本

### 1.1 全仓统计

| 文件 | test 数 | 显式 skip 标记 | 运行时 pytest.skip | 实际被跳过 |
|---|---:|---:|---:|---:|
| apps/core/tests/test_permission_v2.py | 10 | 5 | 0 | **5** |
| apps/core/tests/test_api_v2_user_role.py | 3 | 3 | 0 | **2** |
| apps/core/tests/test_api_v2_role.py | 2 | 3 | 0 | **2** |
| apps/core/tests/test_models_v2.py | 4 | 0 | 1 | **1** |
| apps/core/tests/test_sync_resources_t29.py | 4 | 0 | 3 | **0**（见 §1.3） |
| **合计** | **23** | **11** | **4** | **10**（CI 显示 9 skipped 见 §1.3） |

> 注：CI 报告 "9 skipped" 是因为 `test_sync_resources_t29.py` 的 3 条用了 `pytest.skip()`
> 而非 `@pytest.mark.skip`，运行时跳过不计入 collect 时的 skip 标注。

### 1.2 Skip 原因（按文件）

| 文件 | skip 原因 | 今天是否仍成立 |
|---|---|---|
| test_permission_v2.py | `UserRoleV2/RoleV2 INSERT blocked until T17 v2 schema applied` | **是**：根因即 P0-A（schema 未建） |
| test_api_v2_user_role.py | `UserRoleV2 INSERT blocked until T17 v2 schema` | **是** |
| test_api_v2_role.py | `RoleV2/RolePermissionV2 INSERT blocked until T17 v2 schema` | **是** |
| test_models_v2.py:61 | `user_roles table is V1-schema until T17 (drop_old phase); V2 INSERT round-trip for management_unit_ids JSON deferred to T17/v2_apply_schema` | **是** |
| test_sync_resources_t29.py:55/115/143 | `needs T17 v2 schema (role_permission.resource_code column)` | **部分成立**：见 §1.3 |

### 1.3 ⚠️ 重要发现：3 条 `test_sync_resources_t29_*` 不只是"等 T17"

**实测**：把 `pytest.skip()` 临时注释掉跑这 4 个测试：

```
FAILED apps/core/tests/test_sync_resources_t29.py::test_sync_resources_persists_codes
FAILED apps/core/tests/test_sync_resources_t29.py::test_sync_resources_rejects_invalid_codes
FAILED apps/core/tests/test_sync_resources_t29.py::test_sync_resources_empty_array_clears
3 failed, 11 passed
```

**失败原因**：`django.db.utils.IntegrityError: NOT NULL constraint failed: roles.id`

含义：即使 T17 修了 V2 schema，这 3 条测试也会因 roles 表 NOT NULL 约束与代码不兼容**继续红**。这意味着：

1. **不是"等 T17 自动好"的事**——T01 修完表之后需要额外排查（可能是新建 role 时显式设 id 而不是依赖默认 gen_id、也可能是 schema 加了 NOT NULL 与代码不一致）。
2. **QUARANTINE 里这 3 条不只是 defer，是藏雷**——CI 隔离区看似只是延期，实则是测试和代码都没就位。
3. **同源根因**：与 P0-A 的「`0002_v2_init.py:177` 用 `database_operations=[]` 只注册 state」直接相关——state 与 schema 漂移后，default 生成器（`gen_id`）和数据库 NOT NULL 约束对不齐。

### 1.4 T01 修完后预期会暴露的问题（给架构师/QA 的预判）

1. **3 条 T29 失败可能不是简单解 skip 就能修**——需要核实 roles 表 id 字段是否允许 NULL，或代码在 create role 时是否漏传 id。
2. **10 条被 skip 的 V2 测试从未在真 schema 上跑过**——很可能存在历史 bug 被长期掩盖。T01 解 skip 后预期会一次性炸出多个历史 bug，需要预留修复时间。
3. **`.venv` 下还有 12 处 skip**（autobahn / pytest-django 等第三方依赖），与本项目无关，不计入。

---

## 二、裸 `IsAuthenticated` 真实数量：54（不是 42，不是 15）

### 2.1 三个数字的来源差异（方法论教训）

| 来源 | 数字 | 为什么错 |
|---|---:|---|
| 架构师原文档 | 42 | 推测来自 grep，可能漏算某些格式 |
| 主理人初查 `grep -rn "permission_classes = \[IsAuthenticated\]"` | 15 | 多行声明、格式差异，grep 抓不全 |
| **运行时 URL resolver 内省（权威）** | **54** | 走 DRF 实际路由表 |

### 2.2 权威数字

```
显式声明裸 IsAuthenticated 的 view 类: 53
未声明、继承全局默认(裸)的 view 类:    1
──────────────────────────────────────
合计仅有身份认证、无资源级校验:        54
有额外权限类的:                       58
```

**112 个可路由 view 类里 54 个（48%）没有任何资源级授权**——只要登录就能访问。

### 2.3 可复用的内省脚本

```python
from django.urls import get_resolver

seen = {}
def walk(pats, prefix=''):
    for p in pats:
        if hasattr(p, 'url_patterns'):
            walk(p.url_patterns, prefix + str(p.pattern))
        else:
            cb = getattr(p.callback, 'cls', None) or getattr(p.callback, 'view_class', None)
            if cb:
                seen[cb] = prefix + str(p.pattern)
walk(get_resolver().url_patterns)

from rest_framework.permissions import IsAuthenticated
bare, declared_bare, ok = [], [], []
for cls, url in seen.items():
    pc = getattr(cls, 'permission_classes', None)
    if pc is None:
        continue
    names = [getattr(c, '__name__', str(c)) for c in pc]
    if names == ['IsAuthenticated']:
        if 'permission_classes' in cls.__dict__:
            declared_bare.append((cls.__name__, url))
        else:
            bare.append((cls.__name__, url))
    else:
        ok.append(cls.__name__)
```

**所有"端点数量/覆盖面"统计必须用此方法，源码 grep 会系统性低估。**

---

## 三、全局默认权限是 fail-open（与 BUG-2 同根）

### 3.1 证据

```python
# config/settings/base.py:273
'DEFAULT_PERMISSION_CLASSES': (
    'rest_framework.permissions.IsAuthenticated',
),
```

任何 view **忘了声明 `permission_classes`，就自动变成"任何登录用户可访问"**。默认失效方向是放行。

### 3.2 与已有问题的同根性

| 问题 | 表现 | 共同点 |
|---|---|---|
| BUG-2 | ACL 缺 context → 不脱敏 | 出错就放行 |
| 54 处裸权限 | 忘声明 → 全员可访问 | 出错就放行 |
| `score_batch_task` | 引擎没接 → 编个分数 | 出错就编数据 |
| 11 个 pytest skip | schema 没建 → 标 "等 T17" | 出错就延期 |

**这不是 4 个独立 bug，是同一种工程姿态**：遇到未完成状态时，选择让系统"看起来能用"，而不是明确失败。

### 3.3 T05 必须包括 fail-open 默认值治理

1. `DEFAULT_PERMISSION_CLASSES` 改为 deny-by-default 自定义权限类（未声明即拒绝并记警告）。
2. 全仓扫 `except → return True/None/{}[]` / `getattr(x,'perm',True)` / `except: pass` 等 fail-open 模式（见 §四）。
3. 改成 fail-closed 的迁移风险：可能有一批当前能访问的端点突然 403。需影子模式告警一轮再拦截。

---

## 四、假实现普查（已发现 3 处）

### 4.1 假实现定义

**线上可达 / 返回结构完整 / 数据完全捏造** —— 比 501 stub 更危险。

### 4.2 已发现清单

| # | 位置 | 假在哪 | 是否生产可达 | 危害等级 |
|---|---|---|---|---|
| 1 | `apps/add_candidate/tasks.py:69-108` `score_batch_task` | 按 idx 编造分数，导入 ScoringService 却从不调用；无条件宣称全员 passed | 是（Celery + SSE + Redis owner 校验已完备） | **🔴 高**：HR 拿假分筛人 |
| 2 | `apps/add_candidate/tasks.py:114-120` `send_async_notification_task` | `logger.info` 后返回，前端以为通知已发 | 是（被 `score_batch_task` 在 async 模式下调度） | **🟡 中**：用户感知不到通知 |
| 3 | `apps/add_candidate/services/resume_parser.py:106-114` `_get_affinda_client` dev fallback | `AFFINDA_API_KEY` 空或 `test_*` 时返回 `_mock_parse(file_obj)`；`logger.warning` 标记"仅 dev 用" | **有 env gate**：dev 才返回 mock | **🟢 低**：生产有真实 key 时是真解析 |

### 4.3 同源待排查（grep 命中但需逐一确认）

| 位置 | 备注 |
|---|---|
| `apps/process/services/template_apply.py:126-127` | "简化：按 stage_name 匹配"，需确认业务可接受性 |
| `apps/process/expressions.py:185-186` | "简化：使用单 pass + 优先级栈"，可能是合理简化，需复查 |
| `apps/referral/views.py:91` | "简化的检测逻辑：基于 referrer 与 candidate 部门关系"，需复查 |
| `apps/core/permissions.py:46` | "基于职位角色的候选人查看权限（简化版）" —— 注释承认简化，需评估 |
| `apps/core/views_permission_v2.py:232` | "简化: 返回所有 unit 让 admin 选" —— 权限相关，可能是 bug |

### 4.4 关键代码证据

```python
# apps/add_candidate/tasks.py:69-108 假实现 #1
def score_batch_task(self, candidate_ids, submit_mode, task_id):
    from .sse import broadcast_event
    from .services.scoring import ScoringService   # ← 导入但从不使用
    for idx, cand_id in enumerate(candidate_ids):
        score = 50 + (idx * 10) % 50               # 按数组下标编分数
        passed = score >= 60
        dimensions = [
            {'name': '技术匹配', 'score': 75 + idx % 20},
            ...
        ]
        broadcast_event(task_id, {'event': 'scoring-done', 'data': {...}})
    broadcast_event(task_id, {
        'event': 'task-complete',
        'data': {'summary': {'total': len(candidate_ids), 'passed': len(candidate_ids)}},  # 无条件全员通过
    })
```

而 `apps/add_candidate/services/scoring.py` 的 `ScoringService` 是**完整真实现**（PRD v2 §5.4 四维规则引擎）。**任务绕过它，自己编分数**。

---

## 五、fail-open / fail-silent 模式初步扫描

### 5.1 `except → 显式拒服务`（可接受，未被吞）

```python
# apps/core/views_permission_v2.py:164-168
except (OperationalError, ProgrammingError) as e:
    return Response(
        {'success': False, 'message': f'role_permission 表不可写: {e}'},
        status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
    )
```
✅ 显式 503，调用方知道失败。架构师原担心"被 except → deny 吞掉、静默降级为全员拒绝"——至少在这条上是**真实拒服务**。

### 5.2 `except Exception → 返回宽松结果`（可疑）

```python
# apps/core/views_auth.py:96-100  logout_view
except Exception:
    return Response(
        {'success': False, 'message': '登出失败'},
        status=status.HTTP_400_BAD_REQUEST,
    )
```
粒度过宽，可能掩盖业务 bug。建议缩小到 `except TokenError` / `ExpiredTokenError` 等已知类型。

```python
# apps/entry_condition/services.py:212-213
except Exception:
    return None
```
⚠️ 校验失败返回 None —— 下游调用方如果 `if result is None: pass` 就会跳过校验。

```python
# apps/application/services/stage_transitions.py:229-230 / 242-243
except Exception as e:
    return {'paused': False, 'reason': f'transition_error: {e}'}
except Exception as e:
    return {'resumed': False, 'reason': f'transition_error: {e}'}
```
⚠️ 异常被转成"业务失败"返回，不抛出。日志链路若断就静默失败。

### 5.3 待扫描（明天 agent 恢复后补）

- 全仓 `getattr(x, 'perm', True)` / `getattr(x, 'allowed', True)`
- 全仓 `except: pass` / `except Exception: pass`
- 全仓 `if not user: return True` 类放行
- 全仓 `try: ...; except: return default_value` 且 default 为宽松值

---

## 六、给明天 agent 的任务清单（按优先级）

### P0：T01 权限 schema 归位
依赖本盘点 §1（skip 清单）、§2（54 处裸权限）、§3（fail-open 默认）。

### P1：T02 假实现治理（新增）
- 修复 `score_batch_task`（接入真 `ScoringService`，不要重写它）
- 修复 `send_async_notification_task`（要么真接通知中心，要么返明确错误）
- 评估 §4.3 五个可疑简化点
- 收口 `resume_parser` mock（确认生产 env gate 真的生效）

### P1：T05 测试解隔离 + 失败放开
- 解 11 个 V2 schema skip
- **优先查 §1.3 T29 失败的根因**（NOT NULL 约束 vs gen_id 默认）
- 消灭 54 处裸权限（结合 T01 的 V2 资源码声明）
- 引用 §3 的 fail-open 治理

### P2：fail-open 模式普查 + 治理
- 收口 §5.2 三处可疑 `except Exception`
- 扫全仓 `getattr(..., True)` / `except: pass` / `try/except return None` 等

---

## 七、产出时间线（429 期间纯人工）

| 时间 | 动作 |
|---|---|
| 14:12 | 收到架构师交付 `docs/PHASE2_DESIGN_2026-08-03.md` |
| 14:13-14:44 | QA 独立验证 Phase 0+1（第二轮） |
| 14:44-16:13 | 用户决策 + 架构师设计增补 + QA 定向回归 |
| 16:13 | BUG-3 工程师自修（commit `1e1ed1e`，含 BUG-4 自查自修） |
| 16:13-17:13 | QA 收到 BUG-3 回归指令 + 全仓 skip 盘点指令 |
| ~17:13 | 所有 agent 同时 429 失败 |
| 17:13-? | 主理人接手 §一-§六 盘点 |

---

*文档结束。*