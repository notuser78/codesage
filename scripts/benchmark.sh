#!/bin/bash
set -e

echo "=========================================="
echo "CodeSage Platform - Benchmark Script"
echo "=========================================="

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
DURATION=${DURATION:-60}
CONCURRENCY=${CONCURRENCY:-10}
OUTPUT_DIR=${OUTPUT_DIR:-"./benchmark_results"}

echo "API URL: $API_URL"
echo "Duration: $DURATION seconds"
echo "Concurrency: $CONCURRENCY"
echo "Output directory: $OUTPUT_DIR"

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

# Create output directory
mkdir -p $OUTPUT_DIR

# Check if API is accessible
print_status "Checking API health..."
if ! curl -s "$API_URL/health" > /dev/null; then
    print_error "API is not accessible at $API_URL"
    exit 1
fi

print_status "API is healthy"

# Run benchmarks
print_status "Running benchmarks..."

# API latency test
print_status "Testing API latency..."
curl -o $OUTPUT_DIR/latency.json -s -w "\nHTTP Status: %{http_code}\nTime: %{time_total}s\n" \
    "$API_URL/api/v1/languages" > $OUTPUT_DIR/latency.txt

# Load test with ab (Apache Bench) if available
if command -v ab &> /dev/null; then
    print_status "Running load test with Apache Bench..."
    ab -n 1000 -c $CONCURRENCY -g $OUTPUT_DIR/ab_results.tsv \
        "$API_URL/health" > $OUTPUT_DIR/ab_report.txt 2>&1
else
    print_warning "Apache Bench not installed, skipping load test"
fi

# Run Locust tests if available
if command -v locust &> /dev/null; then
    print_status "Running Locust load test..."
    locust -f tests/locustfile.py \
        --host=$API_URL \
        --run-time=${DURATION}s \
        --headless \
        --users=$CONCURRENCY \
        --spawn-rate=5 \
        --csv=$OUTPUT_DIR/locust
else
    print_warning "Locust not installed, skipping advanced load test"
fi

# Database performance test
print_status "Testing database performance..."
python3 << EOF
import time
import requests
import json

results = {
    "endpoint_tests": [],
    "timestamp": time.time(),
}

endpoints = [
    ("health", "/health"),
    ("languages", "/api/v1/languages"),
    ("rules", "/api/v1/rules"),
]

for name, path in endpoints:
    times = []
    for _ in range(10):
        start = time.time()
        try:
            response = requests.get("$API_URL" + path)
            elapsed = time.time() - start
            times.append(elapsed)
        except Exception as e:
            print(f"Error testing {name}: {e}")
    
    if times:
        results["endpoint_tests"].append({
            "name": name,
            "path": path,
            "avg_latency": sum(times) / len(times),
            "min_latency": min(times),
            "max_latency": max(times),
            "p95": sorted(times)[int(len(times) * 0.95)],
        })

with open("$OUTPUT_DIR/endpoint_latency.json", "w") as f:
    json.dump(results, f, indent=2)

print("Endpoint latency results saved")
EOF

# Generate report
print_status "Generating benchmark report..."
cat > $OUTPUT_DIR/report.md << 'EOF'
# CodeSage Platform Benchmark Report

## Summary

This report contains benchmark results for the CodeSage Platform API.

## Test Configuration

- API URL: $API_URL
- Duration: $DURATION seconds
- Concurrency: $CONCURRENCY

## Results

### Endpoint Latency

See `endpoint_latency.json` for detailed latency metrics.

### Load Test Results

See `ab_report.txt` and `locust_*.csv` for load test results.

## Recommendations

Based on benchmark results:

1. Monitor p95 latency for production SLA compliance
2. Scale workers if throughput is below requirements
3. Optimize database queries if latency is high

EOF

echo ""
echo "=========================================="
print_status "Benchmark complete!"
echo "=========================================="
echo ""
echo "Results saved to: $OUTPUT_DIR/"
echo ""
echo "View results:"
echo "  cat $OUTPUT_DIR/report.md"
echo "  cat $OUTPUT_DIR/endpoint_latency.json"
echo ""
