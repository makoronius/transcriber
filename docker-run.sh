#!/bin/bash
# Helper script to run whisper transcriber with Docker
# Usage: ./docker-run.sh [cpu|gpu] "PLAYLIST_URL" [additional args]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    echo "Install docker-compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

# Parse arguments
MODE=${1:-cpu}
PLAYLIST_URL=$2
shift 2 || true
EXTRA_ARGS="$@"

# Validate mode
if [[ "$MODE" != "cpu" && "$MODE" != "gpu" ]]; then
    echo -e "${RED}Error: Mode must be 'cpu' or 'gpu'${NC}"
    echo "Usage: $0 [cpu|gpu] \"PLAYLIST_URL\" [additional args]"
    exit 1
fi

# Check if URL is provided
if [ -z "$PLAYLIST_URL" ]; then
    echo -e "${YELLOW}No playlist URL provided. Starting interactive shell...${NC}"
    COMMAND="bash"
else
    COMMAND="python transcribe_playlist.py \"$PLAYLIST_URL\" $EXTRA_ARGS"
fi

# GPU-specific checks
if [ "$MODE" == "gpu" ]; then
    # Check if nvidia-smi is available
    if ! command -v nvidia-smi &> /dev/null; then
        echo -e "${RED}Error: nvidia-smi not found. GPU mode requires NVIDIA drivers.${NC}"
        echo "Install NVIDIA drivers and nvidia-docker: https://github.com/NVIDIA/nvidia-docker"
        exit 1
    fi

    echo -e "${GREEN}GPU detected:${NC}"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
fi

# Create necessary directories
mkdir -p yt_downloads logs

# Build the image if it doesn't exist
SERVICE_NAME="whisper-$MODE"
echo -e "${GREEN}Building $SERVICE_NAME image...${NC}"
docker-compose build $SERVICE_NAME

# Run the container
echo -e "${GREEN}Running transcription...${NC}"
echo -e "${YELLOW}Mode: $MODE${NC}"
echo -e "${YELLOW}Command: $COMMAND${NC}"
echo ""

docker-compose run --rm $SERVICE_NAME $COMMAND

echo ""
echo -e "${GREEN}Done! Check the yt_downloads/ directory for results.${NC}"
