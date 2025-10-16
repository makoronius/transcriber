#!/bin/bash

# Remote Gitea Setup Script
# This script deploys Gitea to a remote server via SSH

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"; }

# Configuration
read -p "Enter remote server IP or hostname: " REMOTE_HOST
read -p "Enter SSH username (default: $USER): " REMOTE_USER
REMOTE_USER=${REMOTE_USER:-$USER}
read -p "Enter SSH port (default: 22): " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

SSH_CMD="ssh -p $SSH_PORT $REMOTE_USER@$REMOTE_HOST"
SCP_CMD="scp -P $SSH_PORT"

REMOTE_DIR="/opt/gitea"

log "Testing SSH connection to $REMOTE_HOST..."
if ! $SSH_CMD "echo 'Connection successful'"; then
    error "Cannot connect to remote server. Please check your SSH credentials."
    exit 1
fi

log "✓ SSH connection successful"

# Check if Docker is installed on remote
log "Checking Docker installation on remote server..."
if ! $SSH_CMD "command -v docker &> /dev/null"; then
    error "Docker is not installed on the remote server."
    info "Please install Docker first:"
    info "  curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! $SSH_CMD "command -v docker compose &> /dev/null"; then
    error "Docker Compose is not installed on the remote server."
    info "Please install Docker Compose first."
    exit 1
fi

log "✓ Docker is installed on remote server"

# Create remote directory
log "Creating deployment directory on remote server..."
$SSH_CMD "sudo mkdir -p $REMOTE_DIR && sudo chown $REMOTE_USER:$REMOTE_USER $REMOTE_DIR"

# Generate secure passwords
log "Generating secure credentials..."
DB_PASSWORD=$(openssl rand -hex 16)
WEBHOOK_SECRET=$(openssl rand -hex 32)

# Get server IP from remote
REMOTE_IP=$($SSH_CMD "hostname -I | awk '{print \$1}'" || echo "$REMOTE_HOST")
info "Remote server IP: $REMOTE_IP"

read -p "Enter Gitea domain (default: $REMOTE_IP): " GITEA_DOMAIN
GITEA_DOMAIN=${GITEA_DOMAIN:-$REMOTE_IP}

# Update configuration files
log "Configuring Gitea for remote deployment..."

# Create temporary files with updated configuration
TEMP_DIR=$(mktemp -d)

# Update docker-compose.gitea.yml
sed "s/GITEA__database__PASSWD=.*/GITEA__database__PASSWD=$DB_PASSWORD/" docker-compose.gitea.yml | \
sed "s/GITEA__server__DOMAIN=.*/GITEA__server__DOMAIN=$GITEA_DOMAIN/" | \
sed "s|GITEA__server__ROOT_URL=.*|GITEA__server__ROOT_URL=http://$GITEA_DOMAIN:3000/|" \
> $TEMP_DIR/docker-compose.gitea.yml

# Update docker-compose.webhook.yml
cp docker-compose.webhook.yml $TEMP_DIR/

# Copy other files
cp deploy.sh webhook-server.py Dockerfile.webhook $TEMP_DIR/
cp DEPLOYMENT.md README.md $TEMP_DIR/

# Create .env file
cat > $TEMP_DIR/.env << EOF
WEBHOOK_SECRET=$WEBHOOK_SECRET
DB_PASSWORD=$DB_PASSWORD
EOF

# Copy files to remote server
log "Copying files to remote server..."
$SCP_CMD -r $TEMP_DIR/* $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/

# Make scripts executable
$SSH_CMD "chmod +x $REMOTE_DIR/*.sh $REMOTE_DIR/*.py"

# Start Gitea
log "Starting Gitea on remote server..."
$SSH_CMD "cd $REMOTE_DIR && docker compose -f docker-compose.gitea.yml up -d"

# Wait for Gitea to start
log "Waiting for Gitea to start..."
sleep 10

# Check if Gitea is running
if $SSH_CMD "docker ps | grep -q gitea"; then
    log "✓ Gitea is running!"
else
    error "Gitea failed to start. Checking logs..."
    $SSH_CMD "cd $REMOTE_DIR && docker compose -f docker-compose.gitea.yml logs"
    exit 1
fi

# Cleanup
rm -rf $TEMP_DIR

# Show summary
echo ""
log "═══════════════════════════════════════════════════════════"
log "              REMOTE GITEA SETUP COMPLETE! 🎉"
log "═══════════════════════════════════════════════════════════"
echo ""
info "Gitea Web UI:       http://$GITEA_DOMAIN:3000"
info "Gitea SSH:          ssh://git@$GITEA_DOMAIN:2222"
info "Webhook Secret:     $WEBHOOK_SECRET"
echo ""
info "Next Steps:"
info "1. Open http://$GITEA_DOMAIN:3000 in your browser"
info "2. Complete the initial setup wizard"
info "3. Create an admin account"
info "4. Create a repository"
info "5. Configure webhook (see README.md)"
echo ""
info "To view logs:"
info "  $SSH_CMD 'cd $REMOTE_DIR && docker compose logs -f'"
echo ""
info "To stop Gitea:"
info "  $SSH_CMD 'cd $REMOTE_DIR && docker compose down'"
echo ""
info "Credentials saved on remote server: $REMOTE_DIR/.env"
log "═══════════════════════════════════════════════════════════"
