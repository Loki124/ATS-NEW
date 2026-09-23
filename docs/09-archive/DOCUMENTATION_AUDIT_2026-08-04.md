# ATS-NEW 文档审计报告 (2026-08-04)

> **审计者**: 许清楚（PM）
> **审计日期**: 2026-08-04
> **被审对象**: `README.md` / `technical.md` / `RUNBOOK.md` / `requirements.md` + docs/ 索引
> **HEAD**: `010e4d4` (T01.1 已落地, CI 384 passed / 0 failed)
> **方法**: 读文档 + `git log` + grep 实际代码 + `git ls-files` 参考 docs/ 真实清单

---

## 1. 总览

| 文档 | 行数 | 评估 | 严重度 | 优先级 |
|---|---|---|---|---|
| `README.md` | 174 | 陈旧、链接到部分不存在 docs/，缺状态徽章 | 🟠 中 | P1 |
| `technical.md` | 344 | **灾难级过期**（Node.js/Express/Prisma 栈从未发生） | 🔴 严重 | **P0** |
| `RUNBOOK.md` | 170 | 健康检查路径错误，测试数过期 | 🔴 严重 | **P0** |
| `requirements.md` | 217 | P3 自相矛盾，统计全过期，未提 Phase 2 | 🟠 中 | P1 |

**结论**: 4 份文档全部不达"可在新员工手上指引工作"的标准。其中 `technical.md` 已接近完全不可信（**整段 §2.2/§3/§5/§6/§7 仍写 Express/Prisma/nodemon**，但项目 2026-06 已切 Django/DRF）。

---

## 2. 逐文档评估

### 2.1 `README.md` (174 行)

**整体评价**: 🟡 基本可用但需修正。

| # | 文件:行 | 现状 | 实际 | 行动 |
|---|---|---|---|---|
| L1 | 顶部 | 缺 CI 状态徽章 | CI 真实状态: pytest 384 passed / 0 failed (010e4d4) | **P0** 加徽章 |
| L46-52 | `docs/` 索引 | ARCHITECTURE.md / MIGRATION.md / SETUP.md / CHANGELOG.md / TROUBLESHOOTING.md / PROJECT_PLAN.md | 这些文件**实际存在** ✅ | ✅ 不需改 |
| L46-52 | `docs/` 索引 | 设计文档未列 | 实际有 `docs/09-archive/ARCHITECTURE_REVIEW_2026-08-03.md`、`docs/PHASE2_DESIGN_2026-08-03.md`、`docs/PHASE2_PRECHECK_2026-08-03.md` | **P1** 补链接 |
| L46-52 | `docs/` 索引 | 验证报告未列 | 实际有 `docs/QA_BUG7_VERIFY_2026-08-04.md`、`docs/QA_T011_VERIFY_2026-08-04.md` | **P1** 补链接 |
| L75-79 | "架构变化 (2026-06-29)" 段 | 真实 | — | ✅ |
| L97-99 | "See the Makefile" 链接 | 真实 | — | ✅ |
| L117-122 | "生产启动" 段 | 真实 | systemd `ats-django.service` + `ats-celery.service` + `ats-celery-beat.service` | ✅ |
| L121-122 | "前端要先 `npm run build`" | 真实 | `package.json:10 build: vue-tsc && vite build` | ✅ |
| L131-133 | 前端 `npm run dev` | 真实 | — | ✅ |
| L141-156 | Tech stack 表 | Django 5 + DRF + MySQL 8 + Celery + Redis | 实际 Django 6.0.6 + DRF 3.17.1 | **P1** 修正版本号 |
| L88-90 | Prerequisites | Python 3.11+ / Node.js 20+ / PostgreSQL 16 / Redis 7 | 实际 Python 3.14.6 / MySQL 8 (不是 PostgreSQL) / Redis 7 | **P1** 修正 |
| L120 | "spa_fallback" 描述 | 真实 | — | ✅ |
| 全文 | "已知问题" | 无 | 54 裸权限已修 / BUG-1~7 已修 / T01.1 已落地 | **P1** 加"当前状态"段 |
| L162-169 | 文档索引 | 5 个 docs/ 链接 | 实际有 14 个 docs/.md | **P1** 补完整索引 |

**改动工作量**: 1 小时 / ~30 行 diff。

---

### 2.2 `technical.md` (344 行) — 灾难级

**整体评价**: 🔴 **完全不可信**。

封面 (L3) 写 "Django 6.0 + DRF 3.15"，但正文 §2.2 / §3 / §5 / §6 / §7 仍是 Node.js 时代产物。**这份文档自我矛盾**——读者只看封面会觉得是 Django，看完正文会觉得是 Express：已经形成"误导+假绿"双输。

| # | 文件:行 | 文档说 | 实际 | 行动 |
|---|---|---|---|---|
| L3 | 标题段 | "实际已切到 Django 6.0.6 + DRF 3.15" | ✅ 真实 | — |
| L5 | 状态段 | "28 apps / 60+ 端点 / 78 张表 / 9 业务状态机 / 39 pytest + 132 vitest 全过" | 实际 **30 apps / 148 路由 / 59 业务表(+V2 9 表) / 7 FSMField / 384 pytest + 132 vitest** | **P0** 重写 |
| L6 | "真实架构图见 `docs/ARCHITECTURE.md`" | 有此文件 (323 行) | ✅ 加注 `docs/09-archive/ARCHITECTURE_REVIEW_2026-08-03.md` 才是真审 | **P1** |
| L11-32 | 1.1 架构图 | ASCII 简图 | 实际图见 `docs/09-archive/ARCHITECTURE_REVIEW_2026-08-03.md` §3 | **P0** 改 Mermaid |
| L34-68 | 1.2 技术栈表 | 真实（基本正确） | 但 django-fsm 3.0.1 (非 2.8.1)、Celery 5.6.3 (非 5.4)、Redis 8.0.1 (非 5.0.4) | **P1** 修正 |
| L55 | "django-fsm 2.8.1" | 实装 3.0.1 | — | **P1** |
| L56 | "已废弃, 迁 viewflow.fsm" | 代码零引用, viewflow.fsm 未装 | — | **P0** 删此误导 |
| L57 | "Celery 5.4 + Redis 5.0" | 实装 5.6.3 + 8.0.1 | — | **P1** |
| L75-108 | §2.1 前端项目结构 | 路径叫 `frontend/`, `index.html` 在根 | 实际在 `web/app/`, `index.html` 在 `web/app/` | **P0** |
| L110-140 | §2.2 后端项目结构 | `prisma/schema.prisma`, `backend/src/`, `auth.middleware.js`, `nodemon.json` | **完全是 Node.js 栈**，实际是 `apps/django/apps/<app>/models.py` + `apps/django/config/settings/{base,dev,prod,test}.py` | **P0** 整段重写 |
| L144-183 | §3 API 接口 | `/api/auth/login`, `/api/users/<id>`, `/api/demands/<id>`, `/api/permissions-v2/mou`, `/api/system/config/demand` | 实际 `/api/v1/auth/login`, `/api/v1/users/<id>/`, `/api/v1/demands/<id>/`, `/api/v1/permissions-v2/mou` (但已迁 `/api/v1/mou/`), `/api/v1/system/config/demand` | **P0** 整段重写 |
| L186-224 | §4 数据模型 | `User/Department/Demand/Position/Candidate/Interview/Offer/Onboarding` 7 张表 | 实际 59+ 业务表 + V2 schema (roles 11 列 / user_roles 10 列) | **P0** 整段重写 |
| L226-251 | §5 配置管理 | `frontend/src/config/index.ts` 内容 + `backend/src/config/index.js` 内容 + `backend/.env` | 实际 `web/app/src/config/index.ts` + `apps/django/config/settings/{base,dev,prod,test}.py` + `apps/django/.env` | **P0** 整段重写 |
| L254-266 | §6 端口配置 | 前端 5212 / 后端 5125 / SQLite 文件 | 实际前端 5212 / 后端 8000 / MySQL 8 | **P0** 整段重写 |
| L269-292 | §7 启动命令 | `cd backend && npm run dev` + `cd frontend && npm run dev` | 实际 `cd apps/django && gunicorn config.wsgi:application --bind 127.0.0.1:8000` + `cd web/app && npm run dev` | **P0** 整段重写 |
| L296-313 | §8 安全机制 | JWT 7d / Helmet.js / Rate Limit / CORS | 实际 JWT 60min+7d (rotation+blacklist) / ConditionalCsrfMiddleware / Throttle: anon60 user1000 login5 / django-cors-headers | **P0** 整段重写 |
| L315-321 | §9 技术亮点 | "Prisma ORM → Django ORM" | 已切 2 个月 | **P0** 删 ORM 迁移字眼 |
| L324-339 | §9 关键架构变更 | 2026-06 ~ 2026-08 表 | 真实（基本正确） | ✅ |
| L343-345 | 文档版本 | "V2.0 (2026-08-03)" | 即将本轮改成 V3.0 | **P0** 改版本 |

**改动工作量**: 3-4 小时 / 整段重写约 200 行（保留架构图 Mermaid + 关键模块清单 + 真实表清单）。

**重构原则**:
- 顶部加 2026-08-04 状态快照（30 apps / 148 路由 / 78 表 / 7 FSMField / 384 pytest + 132 vitest）
- 重点重写 §2.2 / §3 / §5 / §6 / §7 / §8 整段
- 保留 §9 关键架构变更（历史记录真实）
- 用 Mermaid 重画架构图（参考 `docs/09-archive/ARCHITECTURE_REVIEW_2026-08-03.md` §3）
- 引用真实模块清单（30 apps 表，参考 `settings/base.py:98-135`）
- 删除"迁 viewflow.fsm"等纯文档臆想

---

### 2.3 `RUNBOOK.md` (170 行)

**整体评价**: 🟠 基本结构可用，但**关键路径错误**+测试数过期。

| # | 文件:行 | 文档说 | 实际 | 行动 |
|---|---|---|---|---|
| L4 | "写于 2026-08-03" | 真实 | — | — |
| L11 | "Python 3.14+" | 真实 (`.venv` 是 3.14.6) | — | ✅ |
| L18 | "brew install python@3.14" | 真实 | — | ✅ |
| L40 | "REDIS_URL=redis://localhost:6379/0" | 真实 | — | ✅ |
| L44 | "loaddata seeds/07_demo_user.json" | 文件存在 | — | ✅ |
| L48 | "启动命令" | `gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2` | ✅ | — |
| L55 | **"http://localhost:8000/api/v1/health/ → {"status":"ok"}"** | **🔴 错** | 实际路径 `/health/`（`config/urls.py:125`），`/api/v1/health/` 返 404 | **P0** 修 |
| L57 | "ADMIN_URL_TOKEN" | 真实 | — | ✅ |
| L78, 83 | "后端 39 tests / 前端 132 tests" | 实际 **384 pytest / 132 vitest** | — | **P0** 修 |
| L88 | "pytest tests/ -v" | 但实际 CI 等价命令是包含 `--deselect` | — | **P1** 提 CI 入口 |
| L96-97 | "V2 schema 缺失" | 已知 T01.1 已修 | — | **P0** 改"已修复" + commit 引用 |
| L101-104 | "V2 fixture 用 raw SQL" | 仍真实 (T01.1 后需重构) | — | ✅ |
| L120-126 | "stub 路由" | 部分真实 (R5 修后部分返 501) | — | **P1** 更新 |
| L128-133 | "5212 / 8000 端口冲突" | 真实 | — | ✅ |
| L156-160 | "生产 systemd / Cloudflare Tunnel / MySQL 8 / Redis 7" | 真实 | — | ✅ |
| 全文 | 紧急回滚 / 调试章节 | 无 | — | **P0** 加 R1/BUG-7 回滚 + Channels 4 已知问题 |
| L141-152 | 关键文件位置 | 真实 | — | ✅ |
| L167-170 | "下一步" | 过时 | — | **P1** 改"Phase 2 进度" |

**改动工作量**: 1.5 小时 / ~40 行 diff（修路径 + 修测试数 + 加紧急回滚段）。

---

### 2.4 `requirements.md` (217 行)

**整体评价**: 🟠 业务方向正确，但**P3 自相矛盾** + 统计全过期 + 未提 Phase 2。

| # | 文件:行 | 文档说 | 实际 | 行动 |
|---|---|---|---|---|
| L3 | "14/14 P0 + 12/12 P1 + 5/5 P3 全部 done" | — | P0/P1 真实 | **P1** 修 P3 状态 |
| L7 | "P0 14/14 ✅ / P1 12/12 ✅ / P3 5/5 ✅ / P2 11/11 ⬜" | **🔴 自相矛盾** | 同文件 L18 "P3 数据治理 5 项 ⬜" | **P0** 修矛盾 |
| L7 | "含 stub 兜底" | 真实 | — | ✅ |
| L8 | "Django 6.0.6 + DRF 3.15" | 实际 DRF 3.17.1 微差 | — | **P2** 顺手修 |
| L9 | "23 项问题清单" | 真实 | — | ✅ |
| L14-19 | "实现进度速览" | P0/P1 已 done | 真实 | ✅ |
| L18 | "P3 数据治理 5 项 ⬜" | **🔴 自相矛盾** | 实际 P3 仍 ⬜（4 个 0-model app） | **P0** 改 |
| L19 | "Tech 债 进行中" | 真实 | — | ✅ |
| L25-31 | "已实现的核心能力" | 真实 | — | ✅ |
| L34-37 | "待补能力" | 真实 | — | ✅ |
| L40-43 | "统计指标" | "21 路由 / 60+ 端点 / 12 测试套件 / 214 测试 / MySQL 9 / 54+ 张表" | 实际 **148 路由 / 60+ 端点 / 23 测试套件 / 384 测试 / MySQL 8 / 78 张表** | **P0** 改 |
| L44-50 | "1. 项目概述" | 真实 | — | ✅ |
| L51-56 | "1.2 项目目标" | 真实 | — | ✅ |
| L80-105 | "2. 功能需求" | 真实 | — | ✅ |
| L181-195 | "4. 非功能性需求" | 真实 | — | ✅ |
| 全文 | "Phase 2" | 未提 | 实际有 T01-T07 任务分解 (`docs/PHASE2_DESIGN_2026-08-03.md`) | **P0** 加 "Phase 2 待办" 章节 |
| 全文 | "Moka 同步 / GDPR" | 仅 GDPR 提及 | 实际 Moka 同步 (mockeUserId)、GDPR (独立 app) | **P1** 交叉引用 |
| L217 | "文档版本: V1.0" | 即将改 | — | **P0** 改版本 |

**改动工作量**: 2 小时 / ~50 行 diff（修了 P3 矛盾 + 修统计 + 加 Phase 2 章节）。

---

## 3. 优先级矩阵

### P0 — 必须改（本期必做）

| 文档 | 改动 | 风险 |
|---|---|---|
| `technical.md` | 整段重写 §2.2 / §3 / §5 / §6 / §7 / §8 + 删"迁 viewflow.fsm"误导 + 改封面版本 | 🔴 新员工最大误解来源 |
| `RUNBOOK.md` | 修 `/api/v1/health/` → `/health/` + 修"39 tests" → "384 passed" + 加"紧急回滚"段（BUG 系列 / R1 migration 修复） | 🔴 路径错误 → `make status` 永远 404 |
| `README.md` | 加 CI 状态徽章 + 改版本号 + 补 docs/ 完整索引 | 🟠 |
| `requirements.md` | 修 P3 矛盾（L3 vs L18）+ 改统计指标 + 加"Phase 2 待办"章节 + 改版本 | 🟠 |

### P1 — 应该改（2 周内）

| 文档 | 改动 |
|---|---|
| `README.md` | 修 Prerequisites (Python 3.14 / MySQL 8) + 修 Tech stack 版本号 + 加"当前阶段 + 已知问题"段 |
| `technical.md` | 修技术栈表细节版本号（django-fsm 3.0.1 / Celery 5.6.3 / Redis 8.0.1） |
| `RUNBOOK.md` | 更新 stub 路由状态（R5 修后部分返 501） + 改"下一步"段指向 Phase 2 |
| `requirements.md` | 细节业务模块（候选人系统 / 招聘流程 / Moka 同步 / GDPR）交叉引用 |

### P2 — 可延后（1 月内）

- 风格 / 排版 / 例子一致性
- 内部链接补充
- 翻译一致性

---

## 4. 改动工作量总览

| 文档 | 改动量 | 时间估 | commit |
|---|---|---|---|
| `docs/DOCUMENTATION_AUDIT_2026-08-04.md` | 新增 ~280 行 | 2 小时 | 本文档 |
| `technical.md` | 整段重写 ~200 行 diff | 4 小时 | T01.2 (本次) |
| `README.md` | ~30 行 diff | 1 小时 | T01.2 (本次) |
| `RUNBOOK.md` | ~40 行 diff | 1.5 小时 | T01.2 (本次) |
| `requirements.md` | ~50 行 diff | 2 小时 | T01.2 (本次) |
| 合计 | 6 份 | 11.5 小时 | 5 commits |

---

## 5. 后续建议

1. **建立文档验证机制**：
   - CI 加 `make docs-check` 跑 `pytest --collect-only` + 验证 `docs/` 链接不悬空
   - 关键数字（端点数 / 测试数 / 表数）写脚本输出，避免人工漂移
2. **建立 README/TECHNICAL/RUNBOOK 验证日期戳**：
   - 顶部加 `最后验证: 2026-08-04 @ HEAD 010e4d4`
   - 配合 `scripts/docs-age.sh` 跑超过 7 天未验证的文档发 warn
3. **建立"`docs/superpowers/` 商业策略**：
   - 当前 `docs/superpowers/plans/` 10+ 份 2026-06 旧计划仍在
   - 建议: 阶段性归档到 `docs/_archive/`
4. **建立"`COMPLIANCE_AUDIT.md` 复核机制**：
   - 架构师已指出：M1/M3/S2/M4/M5/M6/M9 标 ❌/🟡 但未实修
   - 建议: 任何审计文档必须有 QA 独立复核 + 链接到 fix commit

---

**审计完毕**. IS_PASS: YES.

*文档版本: V1.0 (2026-08-04 许清楚 审计)*
