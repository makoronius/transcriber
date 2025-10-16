#!/bin/bash
# add-project.sh - Helper script to add a new project to CI/CD pipeline
# Usage: ./add-project.sh PROJECT_NAME [DOCKER_PORT]

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Configuration
REMOTE_HOST="mark@100.79.70.15"
GITEA_URL="http://100.79.70.15:3000"
API_TOKEN="97a9a761c190eca3936449cf6af9f03a3b78daef"
WEBHOOK_SECRET="98abd84808c394303be92699dfe7a4468747636986754a2c31d66609e8cc85a0"

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: $0 PROJECT_NAME [DOCKER_PORT]"
    echo ""
    echo "Example: $0 my-web-app 5001"
    echo ""
    echo "This will:"
    echo "  1. Create repository in Gitea"
    echo "  2. Add git remote to current directory"
    echo "  3. Create deployment script on remote server"
    echo "  4. Configure webhook for auto-deployment"
    exit 1
fi

PROJECT_NAME="$1"
DOCKER_PORT="${2:-5000}"

log "Setting up project: $PROJECT_NAME"

# Step 1: Create repository in Gitea
log "Creating repository in Gitea..."
REPO_RESPONSE=$(curl -s -X POST \
  -H "Authorization: token $API_TOKEN" \
  -H "Content-Type: application/json" \
  "$GITEA_URL/api/v1/user/repos" \
  -d "{\"name\":\"$PROJECT_NAME\",\"private\":true,\"auto_init\":false}")

if echo "$REPO_RESPONSE" | grep -q "\"name\":\"$PROJECT_NAME\""; then
    log "✓ Repository created successfully"
else
    if echo "$REPO_RESPONSE" | grep -q "already exists"; then
        warn "Repository already exists, continuing..."
    else
        error "Failed to create repository: $REPO_RESPONSE"
    fi
fi

# Step 2: Add git remote
log "Adding git remote 'gitea'..."
REPO_URL="http://100.79.70.15:3000/mark/$PROJECT_NAME.git"

if git remote get-url gitea &>/dev/null; then
    warn "Remote 'gitea' already exists, updating URL..."
    git remote set-url gitea "$REPO_URL"
else
    git remote add gitea "$REPO_URL"
fi

log "✓ Git remote configured: $REPO_URL"

# Step 3: Create deployment script on remote
log "Creating deployment script on remote server..."

ssh "$REMOTE_HOST" "sudo tee /opt/deployment/deploy-$PROJECT_NAME.sh > /dev/null" << EOF
#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "\${GREEN}[\$(date +'%Y-%m-%d %H:%M:%S')]\${NC} \$1"; }
error() { echo -e "\${RED}[ERROR]\${NC} \$1"; }

# Configuration
REPO_URL="http://100.79.70.15:3000/mark/$PROJECT_NAME.git"
DEPLOY_DIR="/opt/$PROJECT_NAME"
BACKUP_DIR="/opt/backups/$PROJECT_NAME"
BRANCH="main"
CONTAINER_NAME="$PROJECT_NAME"

# Backup function
backup() {
    log "Creating backup..."
    mkdir -p "\$BACKUP_DIR"
    TIMESTAMP=\$(date +%Y%m%d_%H%M%S)

    if [ -d "\$DEPLOY_DIR" ]; then
        tar -czf "\$BACKUP_DIR/backup_\$TIMESTAMP.tar.gz" -C "\$DEPLOY_DIR" . 2>/dev/null || true
        log "Backup created: backup_\$TIMESTAMP.tar.gz"

        # Keep only last 5 backups
        cd "\$BACKUP_DIR" && ls -t backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm
    fi
}

# Deploy function
deploy() {
    log "Starting deployment for $PROJECT_NAME..."

    # Clone or pull
    if [ ! -d "\$DEPLOY_DIR/.git" ]; then
        log "Cloning repository..."
        git clone "\$REPO_URL" "\$DEPLOY_DIR"
        cd "\$DEPLOY_DIR"
    else
        cd "\$DEPLOY_DIR"
        log "Pulling latest changes..."
        git fetch origin
        git checkout "\$BRANCH"
        git pull origin "\$BRANCH"
    fi

    COMMIT_HASH=\$(git rev-parse --short HEAD)
    COMMIT_MSG=\$(git log -1 --pretty=%B)
    log "Deploying commit: \$COMMIT_HASH - \$COMMIT_MSG"

    # Deploy with Docker Compose if docker-compose.yml exists
    if [ -f "docker-compose.yml" ]; then
        log "Building and restarting containers..."
        docker compose down || true
        docker compose build --no-cache
        docker compose up -d

        log "Waiting for container to be healthy..."
        timeout=60
        counter=0
        until [ "\$(docker inspect --format='{{.State.Health.Status}}' \$CONTAINER_NAME 2>/dev/null)" == "healthy" ] || [ \$counter -eq \$timeout ]; do
            sleep 1
            counter=\$((counter + 1))
        done

        if [ \$counter -eq \$timeout ]; then
            error "Container failed to become healthy"
            docker compose logs --tail=50
            exit 1
        fi
    else
        log "No docker-compose.yml found, skipping container deployment"
    fi

    log "✓ Deployment successful!"
}

# Main
case "\${1:-deploy}" in
    deploy)
        backup
        deploy
        ;;
    backup)
        backup
        ;;
    logs)
        cd "\$DEPLOY_DIR"
        docker compose logs -f
        ;;
    status)
        cd "\$DEPLOY_DIR"
        docker compose ps
        docker inspect --format='{{.State.Health.Status}}' \$CONTAINER_NAME 2>/dev/null || echo "Container not found"
        ;;
    *)
        echo "Usage: \$0 {deploy|backup|logs|status}"
        exit 1
        ;;
esac
EOF

# Make executable
ssh "$REMOTE_HOST" "sudo chmod +x /opt/deployment/deploy-$PROJECT_NAME.sh"

log "✓ Deployment script created: /opt/deployment/deploy-$PROJECT_NAME.sh"

# Step 4: Configure webhook
log "Setting up webhook for auto-deployment..."

WEBHOOK_RESPONSE=$(curl -s -X POST \
  -H "Authorization: token $API_TOKEN" \
  -H "Content-Type: application/json" \
  "$GITEA_URL/api/v1/repos/mark/$PROJECT_NAME/hooks" \
  -d "{
    \"type\": \"gitea\",
    \"config\": {
      \"url\": \"http://webhook-server:9000/webhook\",
      \"content_type\": \"json\",
      \"secret\": \"$WEBHOOK_SECRET\"
    },
    \"events\": [\"push\"],
    \"active\": true,
    \"branch_filter\": \"main\"
  }")

if echo "$WEBHOOK_RESPONSE" | grep -q "\"id\""; then
    log "✓ Webhook configured successfully"
else
    warn "Webhook configuration may have failed: $WEBHOOK_RESPONSE"
fi

# Summary
echo ""
log "==============================================="
log "Project '$PROJECT_NAME' setup complete!"
log "==============================================="
echo ""
echo "Repository URL: $REPO_URL"
echo "Deployment script: /opt/deployment/deploy-$PROJECT_NAME.sh"
echo ""
echo "Next steps:"
echo ""
echo "  1. Configure git credentials (if not already done):"
echo "     git config credential.helper store"
echo ""
echo "  2. Push your code to Gitea:"
echo "     git push gitea main"
echo "     # Username: mark"
echo "     # Password: $API_TOKEN"
echo ""
echo "  3. Manual deployment:"
echo "     ssh $REMOTE_HOST \"/opt/deployment/deploy-$PROJECT_NAME.sh deploy\""
echo ""
echo "  4. Check deployment status:"
echo "     ssh $REMOTE_HOST \"/opt/deployment/deploy-$PROJECT_NAME.sh status\""
echo ""
echo "  5. View logs:"
echo "     ssh $REMOTE_HOST \"/opt/deployment/deploy-$PROJECT_NAME.sh logs\""
echo ""
log "Automatic deployment via webhook is enabled!"
log "Pushing to 'main' branch will trigger auto-deployment."
