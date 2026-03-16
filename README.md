# CodeSage Platform

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org)

A modular, AI-powered code analysis platform that combines security scanning, performance diagnostics, and maintainability insights using vector search, knowledge graphs, and modern LLMs.

---

## 🌟 Highlights

- **Security Analysis (SAST + AI)**
- **Performance & Complexity Metrics**
- **Semantic Code Search + Knowledge Graph**
- **Model Serving + Prompt Orchestration**
- **Modular microservices (FastAPI, Celery, LLM, Vector DB)**

---

## 🚀 Quick Start (Local Dev)

### 1) Prerequisites
- Docker 24+
- Docker Compose 2.20+
- 16GB RAM (32GB recommended for LLM workloads)
- 50GB free disk space

### 2) Setup
```bash
git clone https://github.com/your-org/codesage-platform.git
cd codesage-platform
cp .env.example .env
# Update .env as needed (API keys, ports, etc.)
```

### 3) Run the stack
```bash
make up
```

### 4) Validate services
```bash
make check-services
```

---

## 🔌 Key Endpoints

| Service | URL | Notes |
|--------|-----|-------|
| API | http://localhost:8000 | Main REST API |
| OpenAPI | http://localhost:8000/docs | Swagger UI |
| Web UI | http://localhost:5173 | Demo frontend |
| LLM Service | http://localhost:8001 | Model inference |
| Knowledge Service | http://localhost:8002 | Graph + vector search |

---

## 🧪 Analyze a Repo (Example)

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@codesage.local","password":"password123"}' | jq -r .access_token)

REPO_ID=$(curl -s -X POST http://localhost:8000/api/v1/repositories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"url":"https://github.com/example/repo","branch":"main"}' | jq -r .id)

curl -X POST http://localhost:8000/api/v1/repositories/${REPO_ID}/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"analysis_types": ["security", "performance", "quality"]}'
```

---

## 🧱 Project Layout

```
codesage-platform/
├── services/        # Microservices (api, analysis, llm, knowledge)
├── shared/          # Shared models & utilities
├── training/        # Model training pipelines
├── clients/         # Web + VS Code extension
├── k8s/             # Kubernetes manifests
├── monitoring/      # Prometheus/Grafana/Jaeger configs
└── tests/           # Unit/integration/end-to-end tests
```

---

## ✅ Development Workflow

### Senior‑Ready Checklist
- [ ] CI runs on PRs (lint + tests)
- [ ] Dependencies are pinned and scanned for vulnerabilities
- [ ] Integration tests cover core API flows
- [ ] Static typing (mypy) + linting (ruff/flake8) enforced
- [ ] Observability (Prometheus, Grafana, tracing) enabled
- [ ] Secrets management and config validation in place
- [ ] Health checks + graceful shutdown handled
- [ ] Docs + onboarding guides kept up to date
- [ ] Production deployment manifests (K8s/Helm) available
- [ ] Monitoring/alerts for key SLAs (error rate, latency)

### Tests
```bash
make test
make test-unit
make test-integration
```

### Formatting & Linting
```bash
make format
make lint
```

### Start local dev stack
```bash
make up
```

---

## 🧩 Deployment

### Docker Compose (Dev)
```bash
make up
```

### Kubernetes (Prod)
```bash
make k8s-deploy
```

---

## 📌 Contributing
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/xxx`)
3. Commit changes (`git commit -m "..."`)
4. Push and open a PR

---

## 📖 License
Apache 2.0 — see [LICENSE](LICENSE)

---

## 💬 Support
- Docs: https://docs.codesage.io
- Issues: https://github.com/your-org/codesage-platform/issues
- Discussions: https://github.com/your-org/codesage-platform/discussions
| LLM Service | http://localhost:8001 | Model serving endpoint |
| Knowledge Service | http://localhost:8002 | Graph/vector search |
| Grafana | http://localhost:3000 | Metrics dashboards |
| Prometheus | http://localhost:9090 | Metrics collection |
| Jaeger | http://localhost:16686 | Distributed tracing |
| Kong Admin | http://localhost:8009 | API Gateway admin |

## Usage

### Analyze a Repository

```bash
# Submit a repository for analysis
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@codesage.local","password":"password123"}' | jq -r .access_token)

REPO_ID=$(curl -s -X POST http://localhost:8000/api/v1/repositories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"url":"https://github.com/example/repo","branch":"main"}' | jq -r .id)

curl -X POST http://localhost:8000/api/v1/repositories/${REPO_ID}/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"analysis_types": ["security", "performance", "quality"]}'
```

### Web Frontend

The repo includes a minimal browser frontend in `clients/web` with a built-in login flow (`/api/v1/auth/login`) and repository analysis trigger.

```bash
# Run only the frontend (API must already be running)
make up
# or: docker compose up -d web

# Open http://localhost:5173
```

### Web Frontend

The repo includes a minimal browser frontend in `clients/web` that can submit repository analysis requests to the API.

```bash
# Run only the frontend (API must already be running)
docker-compose up -d web

# Open http://localhost:5173
```

### VSCode Extension

1. Install the extension from `clients/vscode/`
2. Open the Command Palette (`Ctrl+Shift+P`)
3. Run `CodeSage: Analyze Current File`
4. View results in the CodeSage panel

### Python SDK

```python
from codesage import CodeSageClient

client = CodeSageClient(api_key="your-api-key")

# Analyze code snippet
result = client.analyze_code(
    code="def example(): pass",
    language="python",
    analysis_types=["security", "performance"]
)

# Query knowledge graph
similar = client.find_similar_code(
    code="function vulnerable(input) { eval(input); }",
    top_k=5
)
```

## Development

### Project Structure
```
codesage-platform/
├── services/
│   ├── api/           # FastAPI gateway
│   ├── analysis/      # Celery workers
│   ├── llm/           # Model serving
│   └── knowledge/     # Graph/vector DB service
├── shared/            # Shared models and utilities
├── training/          # Model training pipeline
├── clients/           # Client SDKs and extensions
├── k8s/               # Kubernetes manifests
├── monitoring/        # Observability config
└── tests/             # Test suites
```

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Security scan
make security-scan
```

## Deployment

### Docker Compose (Development)
```bash
make up
```

### Kubernetes (Production)
```bash
make k8s-deploy
```

### Scaling

Horizontal Pod Autoscaling is configured for:
- API Gateway: 2-10 replicas based on CPU/memory
- Workers: 2-20 replicas based on queue depth
- LLM Service: 1-4 replicas based on request latency

## Model Training

### Supervised Fine-Tuning (SFT)
```bash
make train-sft
```

### RLHF Training
```bash
make train-rlhf
```

## Monitoring

### Metrics
- System metrics: CPU, memory, disk, network
- Application metrics: Request latency, throughput, error rates
- Business metrics: Analysis jobs, queue depth, model performance

### Alerts
Configure alerts in Grafana for:
- High error rates (>5%)
- High latency (p99 > 2s)
- Queue backlog (>1000 messages)
- Service downtime

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Support

- Documentation: https://docs.codesage.io
- Issues: https://github.com/your-org/codesage-platform/issues
- Discussions: https://github.com/your-org/codesage-platform/discussions

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [Hugging Face Transformers](https://huggingface.co/docs/transformers/)
- Graph database powered by [Neo4j](https://neo4j.com/)
- Vector search powered by [Weaviate](https://weaviate.io/)
