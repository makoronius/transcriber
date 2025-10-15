#!/bin/bash

# Whisper AI Transcriber - Docker Quick Start Script
# This script helps you quickly set up and run the Docker container

set -e

echo "=========================================="
echo "Whisper AI Transcriber - Docker Setup"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed."
    echo "Please install Docker first. See DOCKER_SETUP.md for instructions."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker compose &> /dev/null; then
    echo "Error: Docker Compose is not available."
    echo "Please install Docker Compose plugin."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    if command -v openssl &> /dev/null; then
        SECRET_KEY=$(openssl rand -hex 32)
        cat > .env << ENVEOF
SECRET_KEY=${SECRET_KEY}
FLASK_ENV=production
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENVEOF
        echo "✓ .env file created with random SECRET_KEY"
    else
        cp .env.example .env
        echo "✓ .env file created from template"
        echo "⚠ Warning: Please change SECRET_KEY in .env file!"
    fi
else
    echo "✓ .env file already exists"
fi

# Create necessary directories
echo "Creating required directories..."
mkdir -p yt_downloads uploads logs backups
echo "✓ Directories created"

# Check for GPU support
echo ""
echo "Checking for GPU support..."
if docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU detected and Docker GPU support is available"
    USE_GPU=true
else
    echo "⚠ No GPU support detected"
    echo "The container will run in CPU mode (slower transcription)"
    USE_GPU=false
    
    # Ask if user wants to continue
    read -p "Continue without GPU? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Build and start
echo ""
echo "Building Docker image..."
docker compose build

echo ""
echo "Starting container..."
docker compose up -d

# Wait for container to be ready
echo ""
echo "Waiting for container to be ready..."
sleep 5

# Check if container is running
if docker compose ps | grep -q "Up"; then
    echo ""
    echo "=========================================="
    echo "✓ Whisper AI Transcriber is running!"
    echo "=========================================="
    echo ""
    echo "Web Interface: http://localhost:5000"
    echo ""
    echo "Useful commands:"
    echo "  - View logs:        docker compose logs -f"
    echo "  - Stop container:   docker compose stop"
    echo "  - Start container:  docker compose start"
    echo "  - Restart:          docker compose restart"
    echo "  - Remove:           docker compose down"
    echo ""
    
    # Show GPU info if available
    if [ "$USE_GPU" = true ]; then
        echo "GPU Info:"
        docker compose exec whisper-web nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "GPU info not available"
        echo ""
    fi
    
    echo "View logs now? (y/n): "
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose logs -f
    fi
else
    echo ""
    echo "❌ Error: Container failed to start"
    echo "Check logs with: docker compose logs"
    exit 1
fi
