# 文档校准报告 · 前端 / 运维 / 产品（Frontend / Ops / Product）
> 最后更新：2026-09-07（依据 git 最后提交）

- **校准日期**：2026-09-07
- **校准范围**（原 Engineer 目标）：根 `README.md`、`docs/README.md`、`docs/01-wiki/06-前端架构` + `07-部署与运行` + `08-测试体系`、`docs/06-runbook/RUNBOOK.md`、`SETUP.md`、`CHANGELOG.md`、`docs/03-product/requirements.md`、`PROJECT_PLAN.md`
- **校准方式**：直接读取代码 + `package.json` 机械核实（列出条目而非 `grep | wc -l`），逐项比对文档事实性陈述。
- **执行人**：主理人齐活林（Qi）直校（原派发 agent 因 429 配额中断，改为本地工具逐份核对）。

---

## 1. 代码侧核实结论（事实基准）

| 指标 | 代码实测 | 文档原口径 | 结论 |
|---|---|---|---|
| 前端 API 客户端 `.ts` 模块（`web/app/src/api/`） | **31** | 31 | ✅ 准确 |
| Pinia store（`web/app/src/stores/`） | **5** | 5 | ✅ 准确 |
| 前端框架版本（`web/app/package.json`） | Vue `^3.4.0` / Vite `^5.0.0` / Naive UI `^2.44.1` / Pinia `^2.1.0` / Vue Router `^4.2.0` / TypeScript `^5.3.0` / vitest `^2.1.9` / UnoCSS `^66.7.0` | 文档一致（个别处 Naive 简写 2.44，与 2.44.1 等价） | ✅ 准确 |
| 业务域页面目录 | 14+ | 14+ | ✅ 准确 |
| 数据库表 / FSM / 路由 / 迁移 / app 数 | 见后端报告（70 / 7 / 105+52 / 105-33 / 35） | 多文档写 78 表 / 148 路由 / 30 apps | ✅ 已随后端报告一并修正 |

---

## 2. 已就地修正（前端 / 运维 / 产品相关）

| 文件 | 行 | 修正前 | 修正后 |
|---|---|---|---|
| `docs/03-product/PROJECT_PLAN.md` | 13 | `29 个 app / 78 张表 / 9 业务状态机` | `35 个 app / 70 张表 / 7 业务状态机` |
| `docs/03-product/requirements.md` | 14 | `业务 + V2 共 78 张表` | `业务 + V2 共 70 张表` |
| `docs/03-product/requirements.md` | 42 | `30 apps / 148 路由 / 49 ViewSet` | `35 apps / 105 path() + 52 router.register / 49 ViewSet` |
| `docs/03-product/requirements.md` | 44 | `78 张表（59 业务 + 9 V2 + 4 V1 + 6 内建）` | `70 张表（含 V2 权限 9 表 + V1 备份 4 表）` |
| `README.md`（根） | 5 | `78 表` | `70 表` |
| `README.md`（根） | 99 | `技术架构 + 30 apps + 78 表` | `技术架构 + 35 apps + 70 表` |
| `docs/01-wiki/07-部署与运行.md` | 155 | `业务数据（78+ 表）` | `业务数据（70 张表）` |
| `docs/01-wiki/README.md` | 45 | `78+ 张表 / 148+ 条 API 路由` | `70 张表 / 105 path() + 52 router.register` |
| `docs/06-runbook/MIGRATION.md` | 8 | `78 张表 / 9 业务状态机` | `70 张表 / 7 业务状态机` |

> 文档索引 `docs/README.md` 的审计表在前序会话已校正（「准确性 🔴 较差」→「🟢 基本准确」，并列出 35/7/31/5 等核实数），本次复核其正文无残留 `30 apps` / `78 表` / `DRF 3.15`，无需再改。
> `06-前端架构`、`08-测试体系`、`RUNBOOK`、`SETUP`、`CHANGELOG` 正文结构/路径/命令经核对无硬错误；仅 pytest/vitest 通过数存在口径冲突（见 §3）。

---

## 3. 待运行时核实（未猜测修改）

- **pytest 通过数四套口径**：`384` / `518` / `772` / `859`（详见后端报告 §3）。前端文档（`08-测试体系`、`CHANGELOG`、`SETUP`、`RUNBOOK`）分别引用其中不同数值，彼此矛盾，**无运行时证据不妄改**。
- **vitest 132 passed**：各文档口径一致（132），但属运行时数值，未独立重跑验证；与「15 个 `.spec.ts` / 29 个 spec」为不同口径（测试文件数 vs 测试函数数 vs 通过数），非错误。
- **建议**：统一为 `make stats` / CI 生成的单一数字，前端 vitest 亦纳入同一来源。

---

## 4. 历史审计 / 评审文档处理说明

同后端报告 §4：`docs/07-audit/*`（DOCUMENTATION_AUDIT / PROJECT_FULL_REVIEW / PRODUCT_AUDIT 等）为带日期快照，含 30 apps / 148 路由 / 78 表 / 384 pytest 等旧值，**本次有意不改写**，建议加「截至日期」横幅或单独刷新。

---

## 5. 结论

前端 / 运维 / 产品类**现行文档**的结构、路径、命令、版本号均准确；规模数字（app/表/路由/迁移/FSM）已随后端报告统一修正为 35 / 70 / 105+52 / 105-33 / 7。唯一残留不一致为测试通过数（pytest 四套口径、vitest 未重跑），需运行时单一事实来源，不属本次可安全修正范围。
