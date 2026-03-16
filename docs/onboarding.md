# Onboarding Guide

This guide helps new contributors get the project running locally and understand the main components.

## 1) Checkout and Setup

```bash
git clone https://github.com/your-org/codesage-platform.git
cd codesage-platform
cp .env.example .env
# Edit .env with real secrets (see `.env.example`)
```

## 2) Start the Development Stack

```bash
make up
```

The stack includes:
- API (FastAPI)
- Analysis worker (Celery)
- LLM service (model inference)
- Knowledge service (Neo4j + Weaviate)

## 3) Run Tests Locally

```bash
make test-unit
make test-integration
```

CI runs the same commands automatically on each PR.

## 4) Lint + Formatting

```bash
make format
make lint
```

## 5) Working with the API

- Open API docs: http://localhost:8000/docs
- Basic health check: http://localhost:8000/health

## 6) Adding a New Feature

1. Create a feature branch (`feature/<name>`)
2. Add or update tests under `tests/`
3. Run `make test` locally
4. Open a PR and wait for CI to pass

## 7) Notes on Secrets

- Production secrets should be stored in a vault (HashiCorp Vault, AWS Secrets Manager, etc.) or GitHub Secrets.
- Do not commit `.env` files or secrets to the repository.

## 8) Troubleshooting

- If services fail to start, inspect logs:
  - `make logs-api`
  - `make logs-worker`
  - `make logs-llm`

- If dependencies fail, re-run:
  ```bash
  make dev-setup
  ```
