# 后端测试覆盖率基线 — 2026-08-06

> 建立人：严过关（QA）
> 基线 commit：`a78020a` + 本次新增测试
> 采集命令：
> ```bash
> cd apps/django && source .venv/bin/activate
> python -m pytest --ds=config.settings.test --cov=apps --cov-report=term-missing --cov-report=html -q
> ```
> HTML 报告：`apps/django/htmlcov/index.html`（未入库，本地查看）
> 工具：pytest-cov 7.1.0（venv 中已预装，无需额外安装）

---

## 1. 总览

| 指标 | 数值 |
| --- | --- |
| 测试用例总数 | **479 passed / 0 failed** |
| 执行耗时 | ~12s |
| **总覆盖率（含 migrations/tests）** | **63%** （14705 语句 / 5383 未覆盖） |
| **业务代码覆盖率（剔除 migrations、tests、`__init__.py`、`apps.py`）** | **57.2%** （11827 语句 / 5062 未覆盖） |
| 纳入统计的业务文件数 | 212 |

> **为什么要给两个数字**：`--cov=apps` 把 migrations 和测试文件本身也算了进去，
> 这两类文件天然接近 100%，会把总数拉高约 6 个百分点。**做决策请以业务代码
> 57.2% 为准**，63% 只用于跟后续 CI 的同口径对比。

### 本次新增测试

| 文件 | 用例数 | 作用 |
| --- | --- | --- |
| `apps/django/tests/test_application_grabpool_nonempty_regression.py` | 14 | **带数据**验证 `GET /api/v1/applications/`、`GET /api/v1/grab-pool/`（a78020a 三个二级 bug 的回归） |
| `apps/django/tests/test_unmasked_routes_http_smoke.py` | 10 | 8 处被打通路由的真实 HTTP 可达性冒烟（补 `resolve()` 层之外的一层） |

新增前 455 → 新增后 479。

---

## 2. 按 app 分组覆盖率（业务代码，升序）

> 🔴 <35%　🟡 35–60%　🟢 >60%

| # | App | 语句数 | 未覆盖 | 覆盖率 | |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | `integration` | 342 | 250 | **26.9%** | 🔴 |
| 2 | `notification` | 345 | 237 | **31.3%** | 🔴 |
| 3 | `invitation` | 268 | 167 | 37.7% | 🟡 |
| 4 | `automation` | 506 | 287 | 43.3% | 🟡 |
| 5 | `onboarding` | 221 | 124 | 43.9% | 🟡 |
| 6 | `application` | 1032 | 572 | 44.6% | 🟡 |
| 7 | `analytics` | 299 | 163 | 45.5% | 🟡 |
| 8 | `time_limit` | 259 | 140 | 45.9% | 🟡 |
| 9 | `process` | 1248 | 665 | 46.7% | 🟡 |
| 10 | `offer` | 251 | 132 | 47.4% | 🟡 |
| 11 | `common` | 401 | 203 | 49.4% | 🟡 |
| 12 | `entry_condition` | 465 | 235 | 49.5% | 🟡 |
| 13 | `position` | 248 | 119 | 52.0% | 🟡 |
| 14 | `audit` | 240 | 106 | 55.8% | 🟡 |
| 15 | `mou` | 307 | 132 | 57.0% | 🟡 |
| 16 | `core` | 1447 | 612 | 57.7% | 🟡 |
| 17 | `referral` | 490 | 204 | 58.4% | 🟡 |
| 18 | `interview` | 198 | 80 | 59.6% | 🟡 |
| 19 | `talent_pool` | 260 | 97 | 62.7% | 🟢 |
| 20 | `channel` | 131 | 48 | 63.4% | 🟢 |
| 21 | `duplicate_check` | 22 | 7 | 68.2% | 🟢 |
| 22 | `scraped_resume` | 55 | 16 | 70.9% | 🟢 |
| 23 | `resume_flow` | 215 | 52 | 75.8% | 🟢 |
| 24 | `demand` | 296 | 54 | 81.8% | 🟢 |
| 25 | `gdpr` | 296 | 54 | 81.8% | 🟢 |
| 26 | `candidate` | 811 | 141 | 82.6% | 🟢 |
| 27 | `field_acl` | 222 | 36 | 83.8% | 🟢 |
| 28 | `add_candidate` | 719 | 110 | 84.7% | 🟢 |
| 29 | `library` | 71 | 6 | 91.5% | 🟢 |
| 30 | `dynamic_field` | 162 | 13 | 92.0% | 🟢 |

**观察**：覆盖率与"该模块最近是否被专项整改过"高度相关。`add_candidate` /
`field_acl` / `dynamic_field` / `candidate` 都是近期做过缺陷整改并补了测试的，
都在 80% 以上；而从未被专项覆盖的 `integration` / `notification` 则垫底。

---

## 3. 覆盖率最低的 10 个业务模块

筛选口径：剔除 migrations / tests / `__init__.py` / `apps.py`，且语句数 ≥ 20
（避免小文件噪声）。

| # | 文件 | 覆盖率 | 语句数 | 未覆盖行数 |
| --- | --- | ---: | ---: | ---: |
| 1 | `apps/integration/services.py` | **0%** | 198 | 198 |
| 2 | `apps/notification/services.py` | **0%** | 176 | 176 |
| 3 | `apps/application/tasks.py` | **0%** | 95 | 95 |
| 4 | `apps/core/management/commands/init_demo_data.py` | **0%** | 93 | 93 |
| 5 | `apps/offer/services.py` | **0%** | 93 | 93 |
| 6 | `apps/application/services/stage_transitions.py` | **0%** | 89 | 89 |
| 7 | `apps/analytics/tasks.py` | **0%** | 84 | 84 |
| 8 | `apps/process/management/commands/load_process_templates.py` | **0%** | 82 | 82 |
| 9 | `apps/process/services/template_apply.py` | **0%** | 79 | 79 |
| 10 | `apps/onboarding/services.py` | **0%** | 77 | 77 |

---

## 4. 高风险低覆盖清单（有业务逻辑且覆盖率 <30%）

口径：业务代码、语句数 ≥ 30、覆盖率 < 30%。
**共 32 个文件，合计 2427 条未覆盖语句 —— 占全部未覆盖语句（5062）的 48%。**

### P0 — 核心业务链路，必须优先补

这些模块直接决定"申请能不能正常流转"，一旦回归就是生产事故：

| 文件 | 覆盖率 | 语句 | 未覆盖 | 风险说明 |
| --- | ---: | ---: | ---: | --- |
| `apps/application/services/stage_transitions.py` | **0%** | 89 | 89 | **阶段流转核心**。申请推进/回退的状态机落地逻辑，零测试。改这里没有任何护栏 |
| `apps/process/expressions.py` | **19%** | 175 | 142 | **进入条件表达式求值器**（`(1 AND 2) OR (3 AND 4)`）。解析器类代码分支极多，19% 等于没测 |
| `apps/entry_condition/services.py` | **27%** | 178 | 130 | 进入条件判定服务，与上一条配套，决定候选人能否进入下一阶段 |
| `apps/automation/services.py` | **24%** | 230 | 175 | 自动化规则引擎，触发条件+动作执行，误触发会批量改数据 |
| `apps/offer/services.py` | **0%** | 93 | 93 | Offer 生成/审批，涉及薪资等敏感字段 |
| `apps/position/services.py` | **0%** | 77 | 77 | 职位状态机（发布/招聘中/关闭）与 headcount 扣减 |
| `apps/time_limit/services.py` | **29%** | 89 | 63 | 阶段限时计算，直接影响超时归档与抢单池准入 |

### P1 — 对外集成 / 通知，失败静默且难排查

| 文件 | 覆盖率 | 语句 | 未覆盖 | 风险说明 |
| --- | ---: | ---: | ---: | --- |
| `apps/integration/services.py` | **0%** | 198 | 198 | **全项目最大的零覆盖文件**。第三方系统同步，失败通常静默 |
| `apps/notification/services.py` | **0%** | 176 | 176 | 消息通知下发。挂了不会报错，只是"用户没收到" |
| `apps/integration/crypto.py` | **0%** | 34 | 34 | **加解密**。零覆盖的加密代码风险极高（密钥/IV/padding 任一错就是数据损坏或泄漏） |
| `apps/invitation/services.py` | **0%** | 66 | 66 | 面试邀约发送 |
| `apps/interview/services.py` | **0%** | 65 | 65 | 面试安排与轮次推进 |
| `apps/channel/services.py` | **0%** | 46 | 46 | 渠道成本核算 |
| `apps/onboarding/services.py` | **0%** | 77 | 77 | 入职流程 |
| `apps/analytics/services.py` | **0%** | 40 | 40 | 报表统计口径 |

### P2 — Celery 异步任务（**整体零覆盖，是一整块系统性盲区**）

| 文件 | 覆盖率 | 语句 |
| --- | ---: | ---: |
| `apps/application/tasks.py` | 0% | 95 |
| `apps/analytics/tasks.py` | 0% | 84 |
| `apps/automation/tasks.py` | 0% | 65 |
| `apps/audit/tasks.py` | 0% | 54 |
| `apps/time_limit/tasks.py` | 0% | 43 |
| `apps/notification/tasks.py` | 0% | 37 |
| `apps/invitation/tasks.py` | 0% | 35 |
| `apps/talent_pool/tasks.py` | 0% | 30 |
| `apps/common/celery_utils.py` | 0% | 69 |

**合计 512 条语句、0 覆盖。** 所有定时/异步逻辑（超时归档、自动流转、报表生成、
审计落库）都没有任何自动化验证。这类代码在生产上出错还特别隐蔽 —— 不影响 HTTP
请求，只是"事情没发生"。建议用 `CELERY_TASK_ALWAYS_EAGER=True` 直接同步调用任务
函数补一批集成测试，成本很低。

### P3 — 基础设施 / 运维脚本

| 文件 | 覆盖率 | 语句 | 备注 |
| --- | ---: | ---: | --- |
| `apps/common/utils.py` | 0% | 48 | 通用工具函数，被广泛引用，零覆盖不合理 |
| `apps/core/middleware_ws.py` | 0% | 39 | WebSocket 中间件（含鉴权） |
| `apps/core/routing.py` | 0% | 31 | WebSocket 路由 |
| `apps/process/services/round_robin_invitation.py` | 0% | 31 | 轮询派单 |
| `apps/core/management/commands/migrate_v2_data.py` | 23% | 53 | V2 数据迁移脚本，**一次性但不可逆** |
| `apps/core/management/commands/init_demo_data.py` | 0% | 93 | 演示数据，优先级低 |
| `apps/process/management/commands/load_process_templates.py` | 0% | 82 | 模板导入 |
| `apps/process/services/template_apply.py` | 0% | 79 | 流程模板应用 |

---

## 5. 本次修复相关文件的覆盖情况

| 文件 | 覆盖率 | 说明 |
| --- | ---: | --- |
| `apps/application/serializers.py` | **88%** | `get_is_in_grab_pool`（119–127 行）本次已被新增测试完整覆盖 |
| `apps/application/urls.py` | 100% | |
| `apps/application/urls_grab_pool.py` | 100% | |
| `apps/application/views.py` | 35% | `GrabPoolViewSet.list` / `summary` 已覆盖；**`reassign` 仍为 0**（544–546 行） |
| `apps/application/services/grab.py` | 36% | `get_pool` 已覆盖；`grab()` / `reassign_overdue()` 未覆盖（112–162、380–398 行） |

### ⚠️ 需要注意的残留缺口

1. **`POST /api/v1/grab-pool/reassign/` 零覆盖**。这是个管理员**批量改数据**的端点，
   而且和整个 GrabPoolViewSet 一样，在 a78020a 之前是**路由不可达的死代码** ——
   也就是说它从上线至今**从未在任何环境被真实调用过**，却在这次修复后突然可达。
   同类的还有 `GrabService.grab()`（含 `select_for_update` 并发控制）。
   建议下一轮优先补。

2. **8 处新打通的子资源端点只做了空表验证**。`test_unmasked_routes_http_smoke.py`
   能挡住 404/500，但挡不住 `SerializerMethodField` 类 bug（那类方法只在有行时
   才执行 —— 这正是 applications 500 藏了这么久的原因）。已静态审计过这 7 个
   子资源的 serializer（只有 FK 直取和 `get_FOO_display`，无 `Model.内部类` 误用），
   暂无发现，但**静态审计不等于测试**。

---

## 6. 覆盖率之外：本次基线暴露的方法论问题

**空表测试会系统性地高估覆盖率的有效性。**

`GET /api/v1/applications/` 这个 bug 能长期存在，不是因为没有测试，而是因为
测试库对应的表是空的 —— `SerializerMethodField` 根本不执行，coverage 也不会
把它标红（那几行是"被执行过"的，只是没有对象走进去）。**行覆盖率天然测不出
这类缺陷。**

因此本文件的百分比只应作为**趋势指标**，不能当作质量结论。配套建议：

1. 列表类端点的测试必须**至少造一条数据**，空表用例只能作为补充；
2. 新增 `SerializerMethodField` / `source='a.b'` 时，必须有带数据的用例；
3. 路由测试要分两层：`resolve()` 层（归属正确）+ HTTP 层（真的不 500）。

---

## 7. 建议的推进目标

| 阶段 | 目标 | 抓手 |
| --- | --- | --- |
| 近期 | 业务代码 57% → **65%** | 补 P0 七个核心 service（stage_transitions / expressions / entry_condition 优先） |
| 中期 | → **75%** | Celery tasks 用 `ALWAYS_EAGER` 整块补齐（512 语句，性价比最高） |
| 长期 | 关键路径行覆盖 ≥ 85% | 把 `--cov-fail-under` 接进 CI，防止倒退 |

**建议立刻接入 CI 的最低门槛**：`--cov-fail-under=63`（当前值，只防倒退不加压）。
待 P0 补完后再逐档上调。
