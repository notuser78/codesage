# CodeSage Platform

An intelligent, AI-powered code analysis platform that provides comprehensive security scanning, performance analysis, and code quality insights using advanced language models and graph-based knowledge representation.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CodeSage Platform                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   VSCode    │  │   Web UI    │  │    CLI      │  │   CI/CD Plugins     │ │
│  │  Extension  │  │  (Future)   │  │  (Future)   │  │   (Future)          │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         └─────────────────┴─────────────────┴────────────────────┘            │
│                                    │                                         │
│                         ┌──────────▼──────────┐                              │
│                         │   Kong API Gateway  │                              │
│                         │  (Rate Limit, Auth) │                              │
│                         └──────────┬──────────┘                              │
│                                    │                                         │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐  │
│  │                                 │         Microservices Layer          │  │
│  │  ┌──────────────┐  ┌───────────▼────────┐  ┌──────────────────────┐  │  │
│  │  │   API Gateway│  │  Analysis Engine   │  │   LLM Service        │  │  │
│  │  │   (FastAPI)  │  │  (Celery Workers)  │  │  (Model Serving)     │  │  │
│  │  │              │  │                    │  │                      │  │  │
│  │  │ • REST API   │  │ • AST Parsing      │  │ • Code Generation    │  │  │
│  │  │ • WebSocket  │  │ • Security Scan    │  │ • Vulnerability Fix  │  │  │
│  │  │ • Auth       │  │ • Performance      │  │ • Explanation        │  │  │
│  │  │ • Rate Limit │  │ • Taint Analysis   │  │ • Refactoring        │  │  │
│  │  └──────────────┘  └────────────────────┘  └──────────────────────┘  │  │
│  │                                                                    │  │
│  │  ┌──────────────────────┐  ┌────────────────────────────────────┐  │  │
│  │  │  Knowledge Service   │  │     Training Pipeline              │  │  │
│  │  │                      │  │                                    │  │  │
│  │  │ • Graph DB (Neo4j)   │  │ • SFT (Supervised Fine-Tuning)   │  │  │
│  │  │ • Vector DB (Weaviate│  │ • RLHF (Reinforcement Learning)  │  │  │
│  │  │ • Code Indexing      │  │ • Dataset Preparation            │  │  │
│  │  │ • Similarity Search  │  │ • Model Evaluation               │  │  │
│  │  └──────────────────────┘  └────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐│
│  │                    Data & Messaging Layer                             ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  ││
│  │  │PostgreSQL│ │  Redis   │ │  Neo4j   │ │ Weaviate │ │  RabbitMQ  │  ││
│  │  │(Metadata)│ │ (Cache)  │ │(Graph DB)│ │(Vectors) │ │  (Queue)   │  ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────────┘  ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      Observability Stack                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │  │
│  │  │  Prometheus  │  │   Grafana    │  │         Jaeger           │  │  │
│  │  │  (Metrics)   │  │(Dashboards)  │  │    (Distributed Tracing) │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features

### Security Analysis
- **Vulnerability Detection**: Identify security flaws using pattern matching and AI-powered analysis
- **Taint Analysis**: Track data flow from sources to sinks to detect injection vulnerabilities
- **OWASP Coverage**: Comprehensive coverage of OWASP Top 10 vulnerabilities
- **SAST Integration**: Static Application Security Testing with detailed remediation guidance

### Performance Analysis
- **Code Complexity**: Cyclomatic and cognitive complexity metrics
- **Hot Path Detection**: Identify performance bottlenecks
- **Resource Usage**: Memory and CPU usage predictions
- **Optimization Suggestions**: AI-powered performance improvement recommendations

### Code Quality
- **AST Parsing**: Deep code understanding using abstract syntax trees
- **Knowledge Graph**: Code relationships and dependencies visualization
- **Semantic Search**: Find similar code patterns across repositories
- **Smart Refactoring**: AI-assisted code restructuring suggestions

## Quick Start

### Prerequisites
- Docker 24.0+
- Docker Compose 2.20+
- 16GB+ RAM (32GB recommended for LLM)
- 50GB+ free disk space

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-org/codesage-platform.git
cd codesage-platform
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start the platform**
```bash
make up
```

4. **Wait for services to be ready**
```bash
make wait-for-services
```

5. **Verify installation**
```bash
make check-services
```

### Accessing Services

| Service | URL | Description |
|---------|-----|-------------|
| API Gateway | http://localhost:8000 | Main REST API |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI documentation |
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
curl -X POST http://localhost:8000/api/v1/repositories/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "https://github.com/example/repo",
    "branch": "main",
    "analysis_types": ["security", "performance", "quality"]
  }'
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
