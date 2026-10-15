# ──────────────────────────────────────────────────────────────
# ATS-NEW monorepo top-level Makefile
# Run `make help` for the full target list.
# ──────────────────────────────────────────────────────────────

SHELL := /bin/zsh
.DEFAULT_GOAL := help
.PHONY: help install backend web clean status test lint

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ────── Bootstrap ──────

install:  ## Install backend + frontend dependencies
	@echo "→ backend deps"
	cd apps/django && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	@echo "→ frontend deps"
	cd web/app && npm install

# ────── Run locally ──────

backend:  ## Run Django backend on :8000
	cd apps/django && . .venv/bin/activate && python manage.py runserver 0.0.0.0:8000

web:  ## Run Vue frontend on :5212
	cd web/app && npm run dev

# ────── Docker stack ──────
# 部署编排 (docker-compose / Dockerfile / nginx.conf / webhook 接收器 / systemd unit)
# 已迁移到独立仓库 ats-deploy-infra (https://gitee.com/loki126/ats-deploy-infra.git)。
# 本仓库只含业务代码, 不再跟踪任何运维/部署文件。本地开发用上面的 backend / web;
# 生产部署 (含 Gitee webhook 自动部署) 全部走 ats-deploy-infra, 详见其 README。

# ────── Quality ──────

status:  ## Show git status + service health
	@git status --short
	@echo "---"
	@curl -s -o /dev/null -w "backend  http://localhost:8000  → %{http_code}\n" http://localhost:8000/health/ || echo "backend  ✗"
	@curl -s -o /dev/null -w "frontend http://localhost:5212  → %{http_code}\n" http://localhost:5212 || echo "frontend ✗"

# ────── Tests / Lint (对齐 CI 能力, 2026-10-09 #42) ──────

test:  ## Run backend + frontend test suites
	cd apps/django && . .venv/bin/activate && pytest -m "not quarantine" --cov=apps --cov-report=term-missing --cov-fail-under=70
	cd web/app && npm test

# 2026-10-15: 防止"新 app 忘了跑 migrate"导致全站 500。
# 事故: position_title/job_level 已注册 INSTALLED_APPS + 迁移在仓, 但本地库未 applied,
#       一进页面就 500 (1146 Table doesn't exist), 排查一度被带偏到代码 bug。
# 以后拉完代码 / 切分支 / 加新 app 后先跑 `make doctor`。
doctor:  ## 检查迁移漂移 + 待应用迁移 + 服务健康
	@echo "→ 1/3 模型与迁移一致性 (有漂移即失败)"
	@cd apps/django && DJANGO_SETTINGS_MODULE=config.settings.dev . .venv/bin/activate && python manage.py makemigrations --check --dry-run
	@echo "→ 2/3 本地库待应用迁移"
	@cd apps/django && . .venv/bin/activate && python manage.py migrate --check || \
		(echo "❌ 有未应用的迁移 —— 执行: cd apps/django && python manage.py migrate" && false)
	@echo "→ 3/3 服务健康"
	@$(MAKE) --no-print-directory status
	@echo "✅ doctor 全绿"

lint:  ## Run Python (ruff) + frontend (eslint) linters
	cd apps/django && . .venv/bin/activate && ruff check apps
	cd web/app && npm run lint

clean:  ## Remove caches and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf web/app/dist apps/django/.venv
	@echo "✓ cleaned"
