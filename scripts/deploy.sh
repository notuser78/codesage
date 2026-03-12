#!/bin/bash
set -e

echo "=========================================="
echo "CodeSage Platform - Deployment Script"
echo "=========================================="

# Configuration
ENVIRONMENT=${1:-staging}
REGISTRY=${REGISTRY:-"codesage"}
VERSION=${VERSION:-"latest"}
NAMESPACE=${NAMESPACE:-"codesage"}

echo "Environment: $ENVIRONMENT"
echo "Registry: $REGISTRY"
echo "Version: $VERSION"
echo "Namespace: $NAMESPACE"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

# Build and push images
build_and_push() {
    local service=$1
    print_status "Building $service image..."
    
    docker build -t $REGISTRY/$service:$VERSION -f services/$service/Dockerfile services/$service/
    
    print_status "Pushing $service image..."
    docker push $REGISTRY/$service:$VERSION
}

# Build all services
print_status "Building Docker images..."
build_and_push "api"
build_and_push "analysis"
build_and_push "llm"
build_and_push "knowledge"

# Update Kubernetes manifests with version
print_status "Updating Kubernetes manifests..."
find k8s/ -name "*.yaml" -exec sed -i "s/:latest/:$VERSION/g" {} \;

# Create namespace if it doesn't exist
print_status "Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply secrets
print_status "Applying secrets..."
kubectl apply -f k8s/secret.yaml -n $NAMESPACE

# Apply configmaps
print_status "Applying configmaps..."
kubectl apply -f k8s/configmap.yaml -n $NAMESPACE

# Deploy infrastructure
print_status "Deploying infrastructure..."
kubectl apply -f k8s/postgres-deployment.yaml -n $NAMESPACE
kubectl apply -f k8s/redis-deployment.yaml -n $NAMESPACE
kubectl apply -f k8s/neo4j-deployment.yaml -n $NAMESPACE
kubectl apply -f k8s/weaviate-deployment.yaml -n $NAMESPACE

# Wait for infrastructure
print_status "Waiting for infrastructure..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s || true

# Deploy application services
print_status "Deploying application services..."
kubectl apply -f k8s/api-deployment.yaml -n $NAMESPACE
kubectl apply -f k8s/worker-deployment.yaml -n $NAMESPACE
kubectl apply -f k8s/llm-deployment.yaml -n $NAMESPACE
kubectl apply -f k8s/knowledge-deployment.yaml -n $NAMESPACE

# Apply ingress
print_status "Applying ingress..."
kubectl apply -f k8s/ingress.yaml -n $NAMESPACE

# Apply HPA
print_status "Applying HPA..."
kubectl apply -f k8s/hpa.yaml -n $NAMESPACE

# Wait for rollout
print_status "Waiting for deployments to complete..."
kubectl rollout status deployment/api -n $NAMESPACE --timeout=300s || true
kubectl rollout status deployment/worker -n $NAMESPACE --timeout=300s || true

# Verify deployment
print_status "Verifying deployment..."
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE
kubectl get ingress -n $NAMESPACE

echo ""
echo "=========================================="
print_status "Deployment complete!"
echo "=========================================="
echo ""
echo "Check status with:"
echo "  kubectl get all -n $NAMESPACE"
echo "  kubectl logs -n $NAMESPACE -l app=api"
echo ""
