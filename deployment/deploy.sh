#!/bin/bash

# Whisper App Deployment Script
# This script pulls the latest code and restarts the application

set -e  # Exit on error

# Configuration
REPO_URL="${REPO_URL:-http://localhost:3000/your-username/whisper.git}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/whisper}"
BRANCH="${BRANCH:-main}"
BACKUP_DIR="${BACKUP_DIR:-/opt/whisper-backups}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Create backup
backup() {
    log "Creating backup..."
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"

    if [ -d "$DEPLOY_DIR" ]; then
        # Backup database and important files
        tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" \
            -C "$DEPLOY_DIR" \
            whisper_jobs.db \
            config.yaml \
            .env \
            2>/dev/null || warn "Some backup files not found"
        log "Backup created: backup_$TIMESTAMP.tar.gz"

        # Keep only last 5 backups
        cd "$BACKUP_DIR" && ls -t backup_*.tar.gz | tail -n +6 | xargs -r rm
    fi
}

# Deploy function
deploy() {
    log "Starting deployment..."

    # Check if directory exists
    if [ ! -d "$DEPLOY_DIR" ]; then
        log "Deploy directory doesn't exist. Cloning repository..."
        git clone "$REPO_URL" "$DEPLOY_DIR"
        cd "$DEPLOY_DIR"
    else
        cd "$DEPLOY_DIR"

        # Check for local changes
        if ! git diff-index --quiet HEAD --; then
            warn "Local changes detected!"
            backup
        fi

        # Pull latest changes
        log "Pulling latest changes from $BRANCH..."
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
    fi

    # Get commit info
    COMMIT_HASH=$(git rev-parse --short HEAD)
    COMMIT_MSG=$(git log -1 --pretty=%B)
    log "Deploying commit: $COMMIT_HASH - $COMMIT_MSG"

    # Build and restart containers
    log "Building and restarting containers..."
    docker compose down
    docker compose build --no-cache
    docker compose up -d

    # Wait for container to be healthy
    log "Waiting for container to be healthy..."
    timeout=60
    counter=0
    until [ "$(docker inspect --format='{{.State.Health.Status}}' whisper-transcriber)" == "healthy" ] || [ $counter -eq $timeout ]; do
        sleep 1
        counter=$((counter + 1))
    done

    if [ $counter -eq $timeout ]; then
        error "Container failed to become healthy"
        log "Container logs:"
        docker compose logs --tail=50
        exit 1
    fi

    log "✓ Deployment successful!"
    log "Application is running at http://localhost:5001"
}

# Rollback function
rollback() {
    log "Rolling back to previous version..."
    cd "$DEPLOY_DIR"
    git reset --hard HEAD~1
    docker compose restart
    log "✓ Rollback complete"
}

# Main execution
case "${1:-deploy}" in
    deploy)
        backup
        deploy
        ;;
    rollback)
        rollback
        ;;
    backup)
        backup
        ;;
    logs)
        cd "$DEPLOY_DIR"
        docker compose logs -f
        ;;
    status)
        cd "$DEPLOY_DIR"
        docker compose ps
        docker inspect --format='{{.State.Health.Status}}' whisper-transcriber
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|backup|logs|status}"
        exit 1
        ;;
esac
