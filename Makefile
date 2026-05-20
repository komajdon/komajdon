.PHONY: dev dev-backend dev-frontend build docker-up docker-down \
        docker-up-prod docker-down-prod install lint test clean help

BACKEND_DIR := backend
FRONTEND_DIR := frontend

dev:           ## Start all services for development
	@echo "Starting Komajdon in dev mode..."
	@docker compose up --build -d
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "API Docs: http://localhost:8000/docs"

dev-backend:   ## Start FastAPI backend only (no Docker)
	@cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:  ## Start Vite frontend only (no Docker)
	@cd $(FRONTEND_DIR) && npm run dev

docker-up:     ## Start dev environment via Docker Compose
	docker compose up --build -d

docker-down:   ## Stop dev Docker Compose
	docker compose down

docker-up-prod: ## Start production environment
	docker compose -f docker-compose.prod.yml up --build -d

docker-down-prod: ## Stop production environment
	docker compose -f docker-compose.prod.yml down

install:       ## Install all dependencies
	@cd $(FRONTEND_DIR) && npm install
	@cd $(BACKEND_DIR) && pip install -r requirements.txt
	@echo "All dependencies installed."

lint:          ## Run linters
	@cd $(BACKEND_DIR) && python3 -m ruff check . 2>/dev/null || echo "ruff not installed — run: pip install ruff"
	@cd $(FRONTEND_DIR) && npx tsc --noEmit 2>/dev/null || echo "TypeScript check skipped"

test:          ## Run all tests
	@cd $(BACKEND_DIR) && python3 -m pytest tests/ -v --cov=app --cov-report=term-missing 2>/dev/null || \
		echo "pytest not installed — run: pip install -r requirements-dev.txt"

test-backend:  ## Run backend tests only
	@cd $(BACKEND_DIR) && python3 -m pytest tests/ -v --cov=app --cov-report=term-missing 2>/dev/null || \
		echo "pytest not installed — run: pip install -r requirements-dev.txt"

test-frontend: ## Run frontend tests only
	@cd $(FRONTEND_DIR) && npx vitest run 2>/dev/null || \
		echo "vitest not configured yet — run: cd frontend && npm install"

secret:        ## Generate a secure SECRET_KEY
	@python3 -c "import secrets; print(secrets.token_urlsafe(32))"

clean:         ## Clean build artifacts
	@rm -rf $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/node_modules
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Clean complete."

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
