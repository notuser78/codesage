COMPOSE ?= $(shell if command -v docker-compose >/dev/null 2>&1; then echo docker-compose; elif command -v docker >/dev/null 2>&1; then echo "docker compose"; else echo docker-compose; fi)

.PHONY: help build up down logs shell test lint format clean deploy k8s-deploy train benchmark

# Default target
help:
	@echo "CodeSage Platform - Available Commands:"
	@echo ""
	@echo "  make build          - Build all Docker images"
	@echo "  make up             - Start all services with $(COMPOSE)"
	@echo "  make down           - Stop all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make shell-api      - Open shell in API container"
	@echo "  make shell-worker   - Open shell in Worker container"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make lint           - Run linting on all Python code"
	@echo "  make format         - Format all Python code"
	@echo "  make clean          - Remove all containers and volumes"
	@echo "  make k8s-deploy     - Deploy to Kubernetes"
	@echo "  make k8s-delete     - Remove from Kubernetes"
	@echo "  make train          - Run model training pipeline"
	@echo "  make benchmark      - Run performance benchmarks"
	@echo ""

# Docker Compose Commands
build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

logs-api:
	$(COMPOSE) logs -f api

logs-worker:
	$(COMPOSE) logs -f worker

logs-llm:
	$(COMPOSE) logs -f llm

# Shell Access
shell-api:
	$(COMPOSE) exec api /bin/sh

shell-worker:
	$(COMPOSE) exec worker /bin/sh

shell-llm:
	$(COMPOSE) exec llm /bin/sh

shell-knowledge:
	$(COMPOSE) exec knowledge /bin/sh

# Database
migrate:
	$(COMPOSE) exec api alembic upgrade head

makemigrations:
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(message)"

# Testing
test:
	pytest tests/ -v --cov=services --cov-report=html --cov-report=term

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-e2e:
	pytest tests/e2e/ -v

# Code Quality
lint:
	flake8 services/ shared/ training/ --max-line-length=100 --exclude=__pycache__,.git
	pylint services/ shared/ training/ --disable=C0111,R0903

format:
	black services/ shared/ training/ --line-length=100
	isort services/ shared/ training/ --profile=black --line-length=100

format-check:
	black --check services/ shared/ training/ --line-length=100
	isort --check-only services/ shared/ training/ --profile=black --line-length=100

# Security
security-scan:
	bandit -r services/ shared/ training/ -f json -o security-report.json || true
	safety check --full-report || true

# Cleaning
clean:
	$(COMPOSE) down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

clean-all: clean
	rm -rf __pycache__ .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Kubernetes
k8s-deploy:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/secret.yaml
	kubectl apply -f k8s/postgres-deployment.yaml
	kubectl apply -f k8s/redis-deployment.yaml
	kubectl apply -f k8s/neo4j-deployment.yaml
	kubectl apply -f k8s/weaviate-deployment.yaml
	kubectl apply -f k8s/llm-deployment.yaml
	kubectl apply -f k8s/api-deployment.yaml
	kubectl apply -f k8s/worker-deployment.yaml
	kubectl apply -f k8s/ingress.yaml
	kubectl apply -f k8s/hpa.yaml

k8s-delete:
	kubectl delete -f k8s/ --ignore-not-found=true

k8s-status:
	kubectl get all -n codesage

k8s-logs-api:
	kubectl logs -n codesage -l app=api -f

k8s-logs-worker:
	kubectl logs -n codesage -l app=worker -f

# Model Training
train:
	python training/pipeline.py --config training/configs/sft_config.yaml --mode sft

train-sft:
	python training/pipeline.py --config training/configs/sft_config.yaml --mode sft

train-rlhf:
	python training/pipeline.py --config training/configs/rlhf_config.yaml --mode rlhf

# Benchmarking
benchmark:
	bash scripts/benchmark.sh

benchmark-api:
	locust -f tests/locustfile.py --host=http://localhost:8000

# Development
dev-setup:
	pip install -r services/api/requirements.txt -r services/analysis/requirements.txt -r services/llm/requirements.txt -r services/knowledge/requirements.txt

check-services:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | jq . || echo "API is not running"
	@curl -s http://localhost:8001/health | jq . || echo "LLM service is not running"
	@curl -s http://localhost:8002/health | jq . || echo "Knowledge service is not running"

# Data Management
backup-db:
	$(COMPOSE) exec postgres pg_dump -U codesage codesage > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db:
	$(COMPOSE) exec -T postgres psql -U codesage codesage < $(file)

# Utilities
wait-for-services:
	@echo "Waiting for services to be ready..."
	@sleep 10
	@make check-services

seed-data:
	curl -X POST http://localhost:8000/admin/seed -H "Authorization: Bearer $(token)"
