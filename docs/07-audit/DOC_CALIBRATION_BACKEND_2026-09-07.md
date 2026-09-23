# 文档校准报告 · 后端 / 架构（Backend & Architecture）

- **校准日期**：2026-09-07
- **校准范围**（原 QA 目标）：`docs/01-wiki/01~05` + `docs/01-wiki/README.md`、`docs/02-architecture/technical.md`、`ARCHITECTURE.md`、`ARCHITECTURE_REVIEW_2026-08-03.md`、`UNIFIED_RULE_ENGINE_DESIGN.md`
- **校准方式**：直接读取代码机械核实（**列出条目而非 `grep | wc -l`**，规避计数陷阱），逐项比对文档事实性陈述。
- **执行人**：主理人齐活林（Qi）直校（原派发的 Engineer/QA agent 因 429 配额中断，改为本地工具逐份核对）。

---

## 1. 代码侧核实结论（事实基准）

| 指标 | 代码实测 | 文档原口径 | 结论 |
|---|---|---|---|
| 本地 app 数（`LOCAL_APPS`，`config/settings/base.py:98-148`） | **35** | 多数已写 35；`technical.md` 写 30 | ✅ 已修正 |
| FSMField 模型定义（candidate/application/demand/position/offer/onboarding/invitation） | **7** | 7 | ✅ 准确 |
| `@transition` 装饰器（models+services，排除测试文件） | **50** | 43（`01-项目概览`/`technical.md`） | ✅ 已修正 |
| 显式 `db_table=` 表（去重） | **70** | 59+9+4=72 或 78 | ✅ 已修正 |
| API 路由：`path()` + `router.register()`（跨 35 个 `urls.py`） | **105 + 52** | 148 显式 + 49 router | ✅ 已修正 |
| 迁移文件 / 目录 | **105 文件 / 33 目录** | 45（technical.md）/ 45（01-项目概览） | ✅ 已修正 |
| Model 类定义（非测试） | ~83 | 78 | ✅ 基本一致 |
| Celery 业务队列（`celery_app.py`） | 8 | 8 | ✅ 准确 |
| 版本：Django 6.0.6 / DRF 3.17.1 / simplejwt 5.5.1 | 实测一致 | 文档一致（个别处 DRF 误写 3.15） | ✅ 已修正 DRF 3.15→3.17.1 |
| Python | 3.14（venv 路径 `python3.14`） | 3.14+ | ✅ 准确 |

> 复用既有审计结论佐证：`PRODUCT_AUDIT.md` 已记录「实测 `db_table` 70 处」「@transition 实测 50」，与本次机械核实一致。

---

## 2. 已就地修正（Backend / 架构相关）

| 文件 | 行 | 修正前 | 修正后 |
|---|---|---|---|
| `docs/02-architecture/technical.md` | 14 | `Django apps **30**` | `**35**` |
| `docs/02-architecture/technical.md` | 16 | `148 条 + 49 router` | `105 条 path() + 52 router.register` |
| `docs/02-architecture/technical.md` | 17 | `43 @transition` | `50 @transition` |
| `docs/02-architecture/technical.md` | 20 | `45 个（24 app, 26 目录）` | `105 个文件 / 33 目录` |
| `docs/02-architecture/technical.md` | 49 | `78 张表` | `70 张表` |
| `docs/02-architecture/technical.md` | 145 | `45 个 migration` | `105 个 migration 文件（33 目录）` |
| `docs/02-architecture/technical.md` | 181 | `（30 apps, 5 分层）` | `（35 apps, 5 分层）` |
| `docs/02-architecture/ARCHITECTURE.md` | 3 | `DRF 3.15, 29 apps / 9 业务状态机` | `DRF 3.17.1, 35 apps / 7 业务状态机` |
| `docs/01-wiki/01-项目概览.md` | 22 | `43 个 @transition` | `50 个 @transition` |
| `docs/01-wiki/01-项目概览.md` | 41 | `59（db_table=）+ V2 9 + V1 4` | `70 张（含 V2 9 + V1 4）` |
| `docs/01-wiki/01-项目概览.md` | 42 | `148 条显式 + 49 router 注册` | `105 个 path() + 52 个 router.register` |
| `docs/01-wiki/01-项目概览.md` | 64 | `全局迁移（45 个）` | `全局迁移（105 个文件 / 33 目录）` |
| `docs/01-wiki/02-整体架构.md` | 27 | `MySQL 8 / 78+ 表` | `MySQL 8 / 70 张表` |
| `docs/01-wiki/04-数据模型与状态机.md` | 23 | `59 张业务表 + V2 9 + V1 4` | `70 张表（含 V2 9 + V1 4）` |
| `docs/01-wiki/README.md` | 45 | `78+ 张表 / 148+ 条 API 路由` | `70 张表 / 105 path() + 52 router.register` |
| `README.md`（根） | 5 | `78 表` | `70 表` |
| `README.md`（根） | 99 | `30 apps + 78 表` | `35 apps + 70 表` |
| `docs/06-runbook/MIGRATION.md` | 8 | `78 张表 / 9 业务状态机` | `70 张表 / 7 业务状态机` |

> `UNIFIED_RULE_ENGINE_DESIGN.md` 经核对无规模数字类硬错误（内容为设计说明），无需修正。
> `ARCHITECTURE_REVIEW_2026-08-03.md` 为 **2026-08-03 评审快照**（含「30 apps / 59 表 / 148 路由 / 27 API 客户端 / 56 ViewSet」），属历史记录，本次**未改写**，见 §4。

---

## 3. 待运行时核实（未猜测修改）

- **pytest 通过数四套口径打架**：`384`（RUNBOOK/SETUP/DOCUMENTATION_AUDIT）、`518`（technical/01-项目概览/08-测试体系/CHANGELOG，2026-08-11 基线）、`772`（PROJECT_FULL_REVIEW_2026-08-26）、`859`（PRODUCT_AUDIT「实测」）。**无运行时证据无法确定当前真值**，故未改动任何一处数字。
- **建议**：建立单一事实来源——`make stats` 或 CI 发布的脚本生成片段，杜绝手抄过期（与 PROJECT_FULL_REVIEW §1 建议一致）。

---

## 4. 历史审计 / 评审文档处理说明

以下为**带日期的审计/评审快照**，本次**有意不改写**（改写会破坏审计轨迹）：
- `docs/09-archive/DOCUMENTATION_AUDIT_2026-08-04.md`（30 apps / 148 路由 / 78 表 / 384 pytest — 08-04 快照）
- `docs/09-archive/PROJECT_FULL_REVIEW_2026-08-26.md`（35 apps / 772 tests — 08-26 快照，PRODUCT_AUDIT 指出 5 天内又漂到 36/859）
- `docs/09-archive/PRODUCT_AUDIT.md`（其「实测 36 apps / 859 def test_」本身也与本次机械核实的 **35 apps** 不符，证明审计文档自身亦在漂移）
- `docs/09-archive/ARCHITECTURE_REVIEW_2026-08-03.md`（08-03 评审）

**建议后续**：为上述文档加「本快照截至 YYYY-MM-DD，数字可能已过期」横幅，或单独发起一轮「审计文档刷新」，并将其中的「实测」数字统一改为脚本生成。

---

## 5. 结论

后端 / 架构类**现行文档**现已口径一致：35 apps、7 FSM、50 @transition、70 表、105 `path()` + 52 `router.register`、105 迁移文件 / 33 目录、DRF 3.17.1。版本号全部准确。唯一残留不一致为 pytest 通过数（需运行时单一来源），不属本次可安全修正范围。
