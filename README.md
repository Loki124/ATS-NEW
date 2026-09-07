# ATS-NEW

> **Applicant Tracking System** — Django 6.0 + DRF 3.17 + Vue 3 monorepo
>
> **状态** (2026-08-04 @ HEAD `010e4d4`): CI 384 passed / 0 failed · 35 apps · 70 表 · 7 状态机
>
> **当前阶段**: Phase 0+1 收口完成（R1-R11 + BUG-1~7 全部修复），Phase 2 T01.1 已落地（V2 权限物理 schema 真实建表），余下 T01.2+ 进行中

Django + Vue 3 monorepo, 部署详见 [RUNBOOK.md](./docs/06-runbook/RUNBOOK.md), 架构详见 [technical.md](./docs/02-architecture/technical.md), 需求详见 [requirements.md](./docs/03-product/requirements.md).

> 📚 **文档中心**：项目全部 **156 份**文档已统一汇总至 [`docs/README.md`](./docs/README.md)，按 9 大主题分类（代码知识库 / 架构 / 产品 / UI / 校招 / 运维 / 审计 / 任务 / 归档），并含文档质量审计结论。**找文档请从该入口进入。**（2026-09-07 汇总，此前文档分散在 18 处）

---

## 仓库布局

```
ATS-NEW/
├── apps/django/                # Django 6.0.6 + DRF 3.17.1 backend (port 8000)
├── web/app/                    # Vue 3 + Vite 5 + Pinia 2 frontend (dev :5212)
├── ops/                        # Docker + nginx + docker-compose
├── docs/                       # 14 份文档 (见下方索引)
├── scripts/                    # 运维脚本
├── Makefile                    # 顶层 make up/backend/web/test
├── README.md                   # 本文档
├── technical.md                # 技术架构
├── RUNBOOK.md                  # 跑通指南 + 紧急回滚
└── requirements.md             # 业务需求
```

---

## 快速启动

### 前置依赖

- **Python 3.14+** (项目 `.venv` 是 3.14.6)
- **Node.js 20+** + npm
- **MySQL 8** (生产) / **SQLite** (dev/test 兜底)
- **Redis 7** (Celery + Channels + 限流)

### 一行启动

```bash
make up          # docker-compose 全栈
make backend     # 仅后端
make web         # 仅前端
```

详见 [Makefile](./Makefile)。

### 手动启动

**后端**（终端 1）:

```bash
cd apps/django
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 编辑 DATABASE_URL / DJANGO_SECRET_KEY / REDIS_URL
python manage.py migrate
python manage.py collectstatic --noinput
python -m gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2
```

**前端**（终端 2）:

```bash
cd web/app
npm install
npm run dev       # http://localhost:5212
npm run build     # vue-tsc + vite build (输出 dist/)
npm test          # 132 vitest
```

健康检查: http://localhost:8000/health/ → `{"status":"ok"}`

---

## 技术栈

| 层 | 技术 |
|---|---|
| Backend | Django 6.0.6 + DRF 3.17.1 + Celery 5.6.3 + Channels 4.3.2 |
| Database | MySQL 8 (生产) / SQLite (dev/test) |
| Auth | JWT (djangorestframework-simplejwt 5.5.1) + V2 权限 (L1-L4 scope) |
| Frontend | Vue 3 + Vite 5 + Pinia 2 + Vue Router 4 |
| UI | Naive UI 2.44 + UnoCSS 66.7 |
| Testing | pytest 9.x (384 passed) / vitest 2.x (132 passed) / Playwright 1.49 |
| 容器 | Docker + docker-compose (R4 修, 含 redis) |
| Proxy | Cloudflare Tunnel (ats.lokisong.cloud → 127.0.0.1:8000) |

---

## 文档索引（14 份）

| 文档 | 用途 |
|---|---|
| [technical.md](./docs/02-architecture/technical.md) | 技术架构 + 35 apps + 70 表 + 19 已修风险 |
| [RUNBOOK.md](./docs/06-runbook/RUNBOOK.md) | 跑通指南 + 紧急回滚按场景 |
| [requirements.md](./docs/03-product/requirements.md) | 业务需求 + Phase 2 待办 |
| [docs/ARCHITECTURE_REVIEW_2026-08-03.md](./docs/02-architecture/ARCHITECTURE_REVIEW_2026-08-03.md) | 架构师深度审计（最权威） |
| [docs/PHASE2_DESIGN_2026-08-03.md](./docs/09-archive/PHASE2_DESIGN_2026-08-03.md) | Phase 2 任务分解 (T01-T07) |
| [docs/PHASE2_PRECHECK_2026-08-03.md](./docs/09-archive/PHASE2_PRECHECK_2026-08-03.md) | Phase 2 预检盘点 |
| [docs/ARCHITECTURE.md](./docs/02-architecture/ARCHITECTURE.md) | 模块图 |
| [docs/CHANGELOG.md](./docs/06-runbook/CHANGELOG.md) | 变更历史 |
| [docs/MIGRATION.md](./docs/06-runbook/MIGRATION.md) | 旧栈迁移日志 |
| [docs/SETUP.md](./docs/06-runbook/SETUP.md) | 详细环境搭建 |
| [docs/TROUBLESHOOTING.md](./docs/06-runbook/TROUBLESHOOTING.md) | 常见问题 |
| [docs/PERFORMANCE.md](./docs/06-runbook/PERFORMANCE.md) | 性能基线 |
| [docs/PROJECT_PLAN.md](./docs/03-product/PROJECT_PLAN.md) | 路线图 |
| [docs/DOCUMENTATION_AUDIT_2026-08-04.md](./docs/07-audit/DOCUMENTATION_AUDIT_2026-08-04.md) | 2026-08-04 文档审计 |
| [docs/QA_T011_VERIFY_2026-08-04.md](./docs/07-audit/QA_T011_VERIFY_2026-08-04.md) | T01.1 QA 验证 |
| [docs/QA_BUG7_VERIFY_2026-08-04.md](./docs/07-audit/QA_BUG7_VERIFY_2026-08-04.md) | BUG-7 QA 验证 |

---

## 当前阶段 / 已知问题

### 阶段

- **Phase 0+1**（止血 + 安全底线）：✅ 全完成（R1-R11 + BUG-1~7 + T01.1）
- **Phase 2**（T01-T07）：🟡 进行中，T01.1 已落地，余下见 `docs/PHASE2_DESIGN_2026-08-03.md`

### 已修复的 19 项问题

| 编号 | 现象 | 修复 commit |
|---|---|---|
| R1 | migration 0004 缺 `import models` | `443550d` |
| R2 | 字段脱敏未接入 | `f4b65ab` |
| R3 | settings 默认回落 dev | `1c0a263` |
| R4 | docker-compose 缺 redis | `0720247` |
| R5/R6 | stub 路由假成功 + 隐藏 login_alias | `e624105` |
| R7 | CI 收集不全 | `9687949` |
| R8 | DEPT scope 折空 | `af5e4a2` |
| R9 | 依赖 lock 漂移 | `7490b05` |
| R10 | vue-tsc 3 error | `e03fda4` |
| R11 | CI 门禁全 `\|\| true` | `9475c6a` |
| R15 | PII 脱敏 | `df78e6f` |
| BUG-1 | 身份证查重失效 | `f8708c9` |
| BUG-2 | 7 处 view 缺 request context | `eae19c3` |
| BUG-3/4 | operator 字段 + id_card_no None | `1e1ed1e` |
| BUG-5 | FSM 5 transition 缺失 | `f970bf8` |
| BUG-6 | 信号审计需显式 | `8213f78` |
| BUG-7 | 迁移 0005 变量遮蔽 | `c60b65f` |
| T01.1 | V2 权限物理 schema 真实建表 | `010e4d4` |

### 残留 QUARANTINE（2 条）

- `test_sync_resources_persists_codes` / `test_sync_resources_rejects_invalid_codes` — fixture 未 seed `permission_templates`，T01.2 启动时补

### 仍待 Phase 2 解决

- 37 个 stub 端点（24 落地 + 3 保留 501 + 10 删）
- 4 个 0-model 空壳 app（scraped_resume / external_sync / duplicate_check / data）
- 103 处 `except Exception`（待分类治理）
- 348 处前端 `any`（待 strict 收敛）
- viewflow.fsm 迁移（代码未启动，仅文档臆想）

---

## License

Proprietary — internal project.
