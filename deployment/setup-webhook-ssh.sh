#!/bin/bash
# Setup SSH authentication for webhook container
set -e

REMOTE_HOST="mark@100.79.70.15"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

log "Setting up webhook SSH authentication..."

# Step 1: Generate SSH key for webhook if it doesn't exist
log "Step 1: Generating SSH key for webhook..."
if [ ! -f "./webhook_id_rsa" ]; then
    ssh-keygen -t rsa -b 4096 -f ./webhook_id_rsa -N "" -C "webhook@container"
    log "SSH key generated"
else
    log "SSH key already exists"
fi

# Step 2: Copy public key to remote server's authorized_keys
log "Step 2: Adding webhook public key to remote server..."
PUBKEY=$(cat webhook_id_rsa.pub)
ssh "$REMOTE_HOST" "mkdir -p ~/.ssh && echo '$PUBKEY' >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
log "Public key added to authorized_keys"

# Step 3: Copy files to remote server
log "Step 3: Copying files to remote server..."
scp webhook-server-ssh.py "$REMOTE_HOST:/opt/deployment/webhook-server-ssh.py"
scp Dockerfile.webhook "$REMOTE_HOST:/opt/deployment/Dockerfile.webhook"
scp docker-compose.webhook.yml "$REMOTE_HOST:/opt/deployment/docker-compose.webhook.yml"
scp webhook_id_rsa "$REMOTE_HOST:/opt/deployment/webhook_id_rsa"
log "Files copied"

# Step 4: Fix permissions on remote
log "Step 4: Setting permissions..."
ssh "$REMOTE_HOST" "chmod 600 /opt/deployment/webhook_id_rsa"

# Step 5: Update docker-compose to mount SSH key
log "Step 5: Updating docker-compose configuration..."
ssh "$REMOTE_HOST" "cat > /opt/deployment/.env << 'EOF'
WEBHOOK_SECRET=98abd84808c394303be92699dfe7a4468747636986754a2c31d66609e8cc85a0
EOF"

# Step 6: Rebuild and restart webhook container
log "Step 6: Rebuilding webhook container..."
ssh "$REMOTE_HOST" "cd /opt/deployment && docker compose -f docker-compose.webhook.yml down"
ssh "$REMOTE_HOST" "cd /opt/deployment && docker compose -f docker-compose.webhook.yml build --no-cache"
ssh "$REMOTE_HOST" "cd /opt/deployment && docker compose -f docker-compose.webhook.yml up -d"

# Step 7: Wait for container to start
log "Step 7: Waiting for webhook container to start..."
sleep 5

# Step 8: Copy SSH key into container
log "Step 8: Setting up SSH in container..."
ssh "$REMOTE_HOST" "docker exec webhook-server mkdir -p /root/.ssh"
ssh "$REMOTE_HOST" "docker cp /opt/deployment/webhook_id_rsa webhook-server:/root/.ssh/id_rsa"
ssh "$REMOTE_HOST" "docker exec webhook-server chmod 600 /root/.ssh/id_rsa"
ssh "$REMOTE_HOST" "docker exec webhook-server sh -c 'echo \"StrictHostKeyChecking no\" > /root/.ssh/config'"
ssh "$REMOTE_HOST" "docker exec webhook-server chmod 600 /root/.ssh/config"

# Step 9: Test SSH connection from container
log "Step 9: Testing SSH connection from container..."
if ssh "$REMOTE_HOST" "docker exec webhook-server ssh -o ConnectTimeout=5 mark@host.docker.internal echo 'SSH test successful'" 2>/dev/null; then
    log "✓ SSH connection test successful!"
else
    warn "SSH connection test failed - trying with localhost..."
    if ssh "$REMOTE_HOST" "docker exec webhook-server ssh -o ConnectTimeout=5 mark@172.17.0.1 echo 'SSH test successful'" 2>/dev/null; then
        log "✓ SSH connection works with 172.17.0.1"
        warn "Update SSH_HOST environment variable to 172.17.0.1"
    else
        warn "SSH connection test failed - you may need to configure manually"
    fi
fi

# Step 10: Check logs
log "Step 10: Checking webhook logs..."
ssh "$REMOTE_HOST" "docker logs webhook-server --tail 20"

echo ""
log "========================================="
log "Webhook SSH setup complete!"
log "========================================="
echo ""
echo "The webhook will now use SSH to trigger deployments on the host."
echo ""
echo "To test the webhook:"
echo "  1. Make a change and commit"
echo "  2. git push gitea main"
echo "  3. Check logs: ssh $REMOTE_HOST 'docker logs webhook-server --tail 50'"
echo ""
echo "To manually trigger deployment:"
echo "  curl -X POST http://100.79.70.15:9000/health"
echo ""
