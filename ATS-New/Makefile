# ──────────────────────────────────────────────────────────────
# ATS-NEW monorepo top-level Makefile
# Run `make help` for the full target list.
# ──────────────────────────────────────────────────────────────

SHELL := /bin/zsh
.DEFAULT_GOAL := help
.PHONY: help install backend web up down logs clean status

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ────── Bootstrap ──────

install:  ## Install backend + frontend dependencies
	@echo "→ backend deps"
	cd apps/django && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	@echo "→ frontend deps"
	cd web/app && pnpm install

# ────── Run locally ──────

backend:  ## Run Django backend on :8000
	cd apps/django && . .venv/bin/activate && python manage.py runserver 0.0.0.0:8000

web:  ## Run Vue frontend on :5173
	cd web/app && pnpm dev

# ────── Docker stack ──────

up:  ## Bring up the full stack via docker-compose
	docker compose -f ops/docker-compose.yml up -d
	@echo "✓ Stack up. Backend :8000  Frontend :8080"

down:  ## Stop the stack
	docker compose -f ops/docker-compose.yml down

logs:  ## Tail logs from all services
	docker compose -f ops/docker-compose.yml logs -f

# ────── Quality ──────

status:  ## Show git status + service health
	@git status --short
	@echo "---"
	@curl -s -o /dev/null -w "backend  http://localhost:8000  → %{http_code}\n" http://localhost:8000/api/v1/health/ || echo "backend  ✗"
	@curl -s -o /dev/null -w "frontend http://localhost:5173  → %{http_code}\n" http://localhost:5173 || echo "frontend ✗"

clean:  ## Remove caches and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf web/app/dist apps/django/.venv
	@echo "✓ cleaned"
