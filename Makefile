.PHONY: up down restart logs migrate migrate-new test-backend test-frontend lint-backend lint-frontend shell-backend shell-db

# Ambiente
up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

# Banco de dados
migrate:
	docker compose exec backend alembic upgrade head

migrate-new:
	@read -p "Descricao da migration: " msg; \
	docker compose exec backend alembic revision --autogenerate -m "$$msg"

migrate-rollback:
	docker compose exec backend alembic downgrade -1

# Testes
test-backend:
	docker compose exec backend pytest --tb=short -q

test-backend-cov:
	docker compose exec backend pytest --cov=. --cov-report=term-missing

test-frontend:
	docker compose exec frontend pnpm test --run

typecheck-frontend:
	docker compose exec frontend pnpm tsc --noEmit

# Qualidade de código
lint-backend:
	docker compose exec backend ruff check .
	docker compose exec backend ruff format --check .

lint-frontend:
	docker compose exec frontend pnpm lint

# Acesso direto
shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec db psql -U fornada -d fornada

# Setup inicial (primeira vez)
setup:
	cp .env.example .env
	docker compose up -d --build
	sleep 5
	docker compose exec backend alembic upgrade head
	@echo "Ambiente pronto! Backend: http://localhost:8000 | Frontend: http://localhost:3000"
