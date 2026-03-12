#!/bin/bash
set -e

echo "=========================================="
echo "CodeSage Platform - Setup Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Detect docker compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version > /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    print_error "Docker Compose is not installed. Please install docker-compose or docker compose plugin first."
    exit 1
fi

print_status "Docker and Docker Compose are installed ($COMPOSE_CMD)"

# Check Docker version
DOCKER_VERSION=$(docker --version | cut -d ' ' -f3 | cut -d ',' -f1)
print_status "Docker version: $DOCKER_VERSION"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p /tmp/repos
mkdir -p /tmp/models
mkdir -p data/postgres
mkdir -p data/redis
mkdir -p data/neo4j
mkdir -p data/weaviate
mkdir -p logs

# Set up environment file
if [ ! -f .env ]; then
    print_status "Creating .env file from template..."
    cp .env.example .env
    print_warning "Please review and update the .env file with your configuration"
fi

# Generate JWT secret if not set
if grep -q "your-super-secret-jwt-key-change-in-production" .env; then
    print_status "Generating JWT secret..."
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i "s/your-super-secret-jwt-key-change-in-production/$JWT_SECRET/g" .env
    print_status "JWT secret generated and saved to .env"
fi

# Pull base images
print_status "Pulling base Docker images..."
${COMPOSE_CMD} pull

# Build services
print_status "Building Docker images..."
${COMPOSE_CMD} build

# Start infrastructure services first
print_status "Starting infrastructure services..."
${COMPOSE_CMD} up -d postgres redis neo4j weaviate rabbitmq

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check PostgreSQL
print_status "Checking PostgreSQL..."
until ${COMPOSE_CMD} exec -T postgres pg_isready -U codesage > /dev/null 2>&1; do
    print_warning "Waiting for PostgreSQL..."
    sleep 2
done
print_status "PostgreSQL is ready"

# Check Redis
print_status "Checking Redis..."
until ${COMPOSE_CMD} exec -T redis redis-cli ping > /dev/null 2>&1; do
    print_warning "Waiting for Redis..."
    sleep 2
done
print_status "Redis is ready"

# Check Neo4j
print_status "Checking Neo4j..."
until curl -s http://localhost:7474 > /dev/null 2>&1; do
    print_warning "Waiting for Neo4j..."
    sleep 2
done
print_status "Neo4j is ready"

# Check Weaviate
print_status "Checking Weaviate..."
until curl -s http://localhost:8080/v1/.well-known/ready > /dev/null 2>&1; do
    print_warning "Waiting for Weaviate..."
    sleep 2
done
print_status "Weaviate is ready"

# Run database migrations (if using Alembic)
# print_status "Running database migrations..."
# ${COMPOSE_CMD} run --rm api alembic upgrade head

# Start all services
print_status "Starting all services..."
${COMPOSE_CMD} up -d

# Wait for services to be ready
print_status "Waiting for application services..."
sleep 15

# Health check
print_status "Performing health checks..."

# Check API
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_status "API Gateway is healthy"
else
    print_warning "API Gateway health check failed - may still be starting"
fi

# Print service URLs
echo ""
echo "=========================================="
echo "CodeSage Platform is starting up!"
echo "=========================================="
echo ""
echo "Service URLs:"
echo "  API Gateway:     http://localhost:8000"
echo "  API Docs:        http://localhost:8000/docs"
echo "  Grafana:         http://localhost:3000 (admin/admin)"
echo "  Prometheus:      http://localhost:9090"
echo "  Jaeger:          http://localhost:16686"
echo "  Neo4j Browser:   http://localhost:7474"
echo "  Weaviate:        http://localhost:8080"
echo "  Kong Admin:      http://localhost:8009"
echo ""
echo "Useful commands:"
echo "  View logs:       ${COMPOSE_CMD} logs -f"
echo "  Stop services:   ${COMPOSE_CMD} down"
echo "  Restart:         ${COMPOSE_CMD} restart"
echo ""
echo "=========================================="
print_status "Setup complete!"
echo "=========================================="
