# ATS-NEW

> **Applicant Tracking System** — Django REST Framework + Vue 3 monorepo.

A modern ATS platform rebuilt from the Node.js legacy backend to a clean
Django + Vue 3 architecture. This monorepo contains the entire stack as
independently deployable services.

---

## Repository layout

```
ATS-NEW/
├── apps/
│   └── django/              # Django REST Framework backend
│       ├── apps/            # 28+ business apps
│       ├── config/          # Project settings (base / dev / prod)
│       ├── libs/            # Cross-cutting utilities
│       ├── tests/           # Pytest suite
│       ├── manage.py
│       └── requirements.txt
│
├── web/                     # Frontend workspace
│   └── app/                 # Vue 3 + Vite + Pinia + Vue Router SPA
│       ├── src/             # Components, views, stores, composables
│       ├── e2e/             # Playwright end-to-end tests
│       ├── package.json
│       └── vite.config.ts
│
├── ops/                     # Operations & deployment
│   ├── docker/              # Dockerfiles
│   ├── nginx/               # Reverse proxy configs
│   └── docker-compose.yml   # One-command local stack
│
├── docs/                    # All project documentation
│   ├── README.md            # Project overview
│   ├── ARCHITECTURE.md
│   ├── MIGRATION.md         # Node.js → Django migration log
│   ├── SETUP.md
│   ├── CHANGELOG.md
│   └── ...
│
├── scripts/                 # Local helper scripts
└── tools/                   # Data seeds, fixtures, dev utilities
```

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
cp .env.example .env  # then edit
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

**Frontend** (terminal 2):

```bash
cd web/app
pnpm install
pnpm dev          # http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`, so the
frontend talks to the backend seamlessly with no CORS configuration.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + DRF + Celery + Redis |
| Database | PostgreSQL 16 (SQLite for local dev) |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Frontend | Vue 3 + Vite + Pinia + Vue Router |
| UI | Element Plus + custom design system |
| Testing | pytest (backend) / Playwright (e2e) |
| Container | Docker + docker-compose |
| Proxy | Nginx |

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
