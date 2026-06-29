# ATS-NEW

> **Applicant Tracking System** — Django REST Framework + Vue 3 monorepo.

A modern ATS platform rebuilt from the Node.js legacy backend to a clean
Django + Vue 3 architecture. This monorepo contains the entire stack as
independently deployable services.

---

## Repository layout

```
ATS-NEW/                                  # 项目根 (2026-06-29 拍平后, 无 ATS-New/ATS-New 嵌套)
├── apps/
│   └── django/              # Django REST Framework backend (port 8000)
│       ├── apps/            # 28+ business apps (candidate / process / application / ...)
│       ├── config/          # Project settings (base / dev / prod / test)
│       ├── tests/           # Pytest suite (test_audit, test_candidate, ...)
│       ├── scripts/         # 内部运维脚本 (init.sh, create_tables_sql.py)
│       ├── seeds/           # 初始化数据 (01_system_stages.json, ...)
│       ├── staticfiles/     # collectstatic 输出 (whitenoise 服务 /static/*)
│       ├── manage.py
│       └── requirements.txt
│
├── web/                     # Frontend workspace
│   └── app/                 # Vue 3 + Vite + Pinia + Vue Router SPA (dev port 5212)
│       ├── src/             # Components, views, stores, composables
│       │   ├── api/         # 后端 API 客户端 (含 dict.ts P0-1 stub)
│       │   ├── components/  # 通用组件 + dashboard / common / candidate
│       │   ├── pages/       # 路由页面 (Layout / Login / Dashboard / settings / ...)
│       │   ├── stores/      # Pinia stores (addCandidate, user, ...)
│       │   └── router/      # vue-router 4 + RBAC 守卫
│       ├── e2e/             # Playwright end-to-end tests
│       ├── package.json
│       ├── vite.config.ts   # target: es2022, target=es2022 (top-level await)
│       ├── tsconfig.json    # target: ES2022 + strict mode
│       ├── eslint.config.js # ESLint 9 flat config (Vue3 + TS)
│       └── dist/            # vite build 输出 (collectstatic 也抓这里)
│
├── ops/                     # Operations & deployment
│   ├── docker/              # Dockerfiles
│   ├── nginx/               # Reverse proxy configs
│   └── docker-compose.yml   # One-command local stack (backend context=../apps/django)
│
├── docs/                    # All project documentation
│   ├── README.md            # 项目索引 (文档入口)
│   ├── ARCHITECTURE.md      # 系统架构 + 模块图
│   ├── MIGRATION.md         # Node.js → Django migration log
│   ├── SETUP.md             # 详细环境搭建
│   ├── CHANGELOG.md         # 变更历史
│   └── TROUBLESHOOTING.md   # 常见问题排查
│
├── scripts/                 # Ops scripts (2026-06-29 拍平后纳入 git)
│   ├── webhook.js           # ⚠️ 已停用 (systemd ats-webhook.service masked)
│   ├── webhook-deploy.sh    # ⚠️ 手动部署入口 (不再触发)
│   ├── e2e-smoke.sh         # Playwright 烟雾测试
│   ├── rotate-mysql-password.sh  # MySQL 密码轮换
│   ├── webhook.service      # systemd unit (被 mask, 保留文件作为历史)
│   └── webhook-setup.md     # 旧 webhook 部署文档 (仅供历史参考)
│
├── Makefile                 # 顶层 make up/backend/web/test
├── config.json              # 项目元数据
├── requirements.md          # 业务需求
└── technical.md             # 技术选型 + 架构决定
```

> **scripts/ 说明**:
> - `webhook.js` + `webhook.service` — Gitee 推送触发的部署接收器（**自 2026-06-29 已停用**，Gitee 端 webhook 已关）
> - `webhook-deploy.sh` — 手动部署入口（不再被自动触发）
> - `e2e-smoke.sh` — Playwright 烟雾测试
> - `rotate-mysql-password.sh` — MySQL 密码轮换
> - `webhook-setup.md` — 旧 webhook 部署文档（仅供历史参考）

> **架构变化 (2026-06-29)**:
> 1. **拍平** `/ATS-New/ATS-New/` 三层嵌套 → 两层 `ATS-New/{代码}`, Gitee HEAD=`6e613d4d`
> 2. **ATS 服务端口**: 旧 9906/9908 (Node.js legacy / recruit) → **新 8000 (Django + gunicorn)**
> 3. **CF Tunnel**: dashboard 端 API-managed, 配置文件是过期 snapshot

---

## Quick start

### Prerequisites

- **Python 3.11+** with `venv`
- **Node.js 20+** with `pnpm` (or `npm`)
- **PostgreSQL 16** (or SQLite for dev)
- **Redis 7** (Celery broker + cache)

### One-command launch

```bash
make up          # bring up the full stack with docker-compose
make backend     # or just the backend
make web         # or just the frontend
```

See the [Makefile](./Makefile) for all targets.

### Manual launch

**Backend** (terminal 1):

```bash
cd apps/django
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 或者用 uv: uv pip install -r requirements.txt
cp .env.example .env  # then edit (DATABASE_URL / REDIS_URL / JWT_SECRET_KEY)
python manage.py migrate
python manage.py collectstatic --noinput    # whitenoise 静态资源 (含前端 dist)
python manage.py test                        # pytest 等价入口
python -m gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2
```

> **生产启动**: `systemd: ats-django.service` (loki 用户), WorkingDirectory=`/opt/ats/ATS-New/apps/django`,
>  Environment=`DJANGO_SETTINGS_MODULE=config.settings.prod`, gunicorn 绑 `127.0.0.1:8000`.
> 同时 `ats-celery.service` + `ats-celery-beat.service` 异步任务.
> 前端 SPA 是 Django 自己 serve: `spa_fallback` 在 `urls.py` 把未匹配的路径 fallback 到 `web/app/dist/index.html`.
> 静态资源用 `whitenoise.CompressedManifestStaticFilesStorage` 直接从 `STATIC_ROOT` serve.
> 前端要先 `npm run build`, 然后 `manage.py collectstatic` 把 `web/app/dist/` 一并拷到 `STATIC_ROOT`.

**Frontend** (terminal 2):

```bash
cd web/app
npm install                         # pnpm 也行
npm run dev                        # http://localhost:5212
npm run build                      # vue-tsc + vite build (输出 dist/)
npm run build:nocheck              # vite build (跳 TS 检查, CI 用)
npm run lint                       # ESLint 9 flat config
npm run test                       # vitest (前端单元)
```

> **前端 dev 端口**: 5212 (之前老的 5173 已不用, vite.config.ts `server.port` = 5212). 
>   Vite dev server 代理 `/api/*` → `http://localhost:8000`, 所以前端零配置跨域.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + DRF + Celery + Redis |
| Database | MySQL 8 (SQLite for test) |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Frontend | Vue 3 + Vite 5 + Pinia 2 + vue-router 4 |
| UI lib | Naive UI 2.44 |
| CSS | UnoCSS |
| Type check | vue-tsc (TypeScript 5, target ES2022) |
| Lint | ESLint 9 (flat config) + eslint-plugin-vue + typescript-eslint |
| Testing | pytest 9 (backend) / vitest 2 (frontend) / Playwright (e2e) |
| Container | Docker + docker-compose |
| Proxy / TLS | Cloudflare Tunnel (server-independent) |
| ATS web access | `https://ats.lokisong.cloud` → CF Tunnel → `127.0.0.1:8000` (gunicorn) |

---

## Documentation

| Doc | Purpose |
|---|---|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System architecture & module map |
| [MIGRATION.md](./docs/MIGRATION.md) | Node.js → Django migration log |
| [SETUP.md](./docs/SETUP.md) | Detailed setup walkthrough |
| [CHANGELOG.md](./docs/CHANGELOG.md) | Release history |
| [PROJECT_PLAN.md](./docs/PROJECT_PLAN.md) | Roadmap |

---

## License

Proprietary — internal project.
