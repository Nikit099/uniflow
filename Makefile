.PHONY: up down test lint build demo-reset openapi

up:
	docker compose up --build

down:
	docker compose down

test:
	.venv/bin/pytest apps/api/tests -q
	cd apps/web && npm test

lint:
	.venv/bin/ruff check apps/api/app apps/api/tests
	.venv/bin/mypy apps/api/app
	cd apps/web && npm run lint && npm run typecheck

build:
	cd apps/web && npm run build
	docker compose build

demo-reset:
	docker compose down -v
	docker compose up --build -d

openapi:
	PYTHONPATH=apps/api .venv/bin/python scripts/export_openapi.py

