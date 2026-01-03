.PHONY: help db-up db-down migrate run-api run-ui run-worker test lint format smoke

help:
	@echo "Available commands:"
	@echo "  make db-up       - Start PostgreSQL database"
	@echo "  make db-down     - Stop PostgreSQL database"
	@echo "  make migrate     - Run database migrations"
	@echo "  make run-api     - Run FastAPI server"
	@echo "  make run-ui      - Run Streamlit UI"
	@echo "  make run-worker  - Run worker"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linter"
	@echo "  make format      - Format code"
	@echo "  make smoke       - Run smoke test (db-up → migrate → smoke)"

db-up:
	docker-compose up -d postgres

db-down:
	docker-compose down

migrate:
	python -m alembic upgrade head

run-api:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

run-ui:
	streamlit run apps/ui/main.py --server.port 8501

run-worker:
	python -m apps.worker.main

test:
	pytest tests/ -v

lint:
	ruff check .
	black --check .

format:
	ruff check . --fix
	black .

smoke: db-up migrate
	@echo "Running smoke test..."
	@mkdir -p artifacts
	@python scripts/smoke.py 2>&1 | tee artifacts/smoke.log || (echo "Smoke test failed" && exit 1)

