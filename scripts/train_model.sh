#!/bin/bash
set -e

echo "=========================================="
echo "CodeSage Model Training Pipeline"
echo "=========================================="

# Configuration
TRAINING_MODE=${1:-"sft"}  # sft or rlhf
CONFIG_FILE=${2:-"training/configs/sft_config.yaml"}
OUTPUT_DIR=${3:-"./output"}

echo "Training mode: $TRAINING_MODE"
echo "Config file: $CONFIG_FILE"
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

# Check if running in Docker or locally
if [ -f /.dockerenv ]; then
    print_status "Running inside Docker container"
    IN_DOCKER=true
else
    print_status "Running locally"
    IN_DOCKER=false
fi

# Create output directory
mkdir -p $OUTPUT_DIR

# Set up Python environment if needed
if [ "$IN_DOCKER" = false ]; then
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    print_status "Installing dependencies..."
    pip install -r training/requirements.txt
fi

# Run training
print_status "Starting $TRAINING_MODE training..."

if [ "$TRAINING_MODE" = "sft" ]; then
    python training/pipeline.py \
        --mode sft \
        --config $CONFIG_FILE \
        --output_dir $OUTPUT_DIR/sft
elif [ "$TRAINING_MODE" = "rlhf" ]; then
    python training/pipeline.py \
        --mode rlhf \
        --config $CONFIG_FILE \
        --output_dir $OUTPUT_DIR/rlhf \
        --base_model $OUTPUT_DIR/sft/final
else
    print_error "Unknown training mode: $TRAINING_MODE"
    exit 1
fi

print_status "Training complete!"
print_status "Model saved to: $OUTPUT_DIR/$TRAINING_MODE/final"

# Upload to model registry (optional)
if [ ! -z "$MODEL_REGISTRY" ]; then
    print_status "Uploading model to registry..."
    # Add your model registry upload logic here
fi

echo ""
echo "=========================================="
print_status "Training pipeline complete!"
echo "=========================================="
