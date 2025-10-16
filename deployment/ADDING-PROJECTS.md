# Adding New Projects to CI/CD

This guide explains how to add additional projects to your Gitea CI/CD infrastructure.

## Development API Key

**Access Token**: `97a9a761c190eca3936449cf6af9f03a3b78daef`

Use this token for programmatic access to Gitea API:

```bash
# Example: List repositories
curl -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  http://100.79.70.15:3000/api/v1/user/repos

# Example: Create new repository
curl -X POST -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  -H "Content-Type: application/json" \
  http://100.79.70.15:3000/api/v1/user/repos \
  -d '{"name":"new-project","private":true}'
```

## Quick Start: Add New Project

### Step 1: Create Repository in Gitea

**Option A: Via Web UI**
1. Go to http://100.79.70.15:3000
2. Click "+" → "New Repository"
3. Enter repository name
4. Click "Create Repository"

**Option B: Via API**
```bash
curl -X POST -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  -H "Content-Type: application/json" \
  http://100.79.70.15:3000/api/v1/user/repos \
  -d '{"name":"PROJECT_NAME","private":true,"auto_init":false}'
```

### Step 2: Add Gitea Remote to Your Local Project

```bash
cd /path/to/your/project
git remote add gitea http://100.79.70.15:3000/mark/PROJECT_NAME.git

# Or if already exists, update it:
git remote set-url gitea http://100.79.70.15:3000/mark/PROJECT_NAME.git
```

### Step 3: Configure Git Credentials

```bash
# Store access token for this repository
git config credential.helper store
git config user.name "mark"
git config user.email "mark@example.com"

# Push to Gitea (will prompt for password - use access token)
git push gitea main
# Username: mark
# Password: 97a9a761c190eca3936449cf6af9f03a3b78daef
```

### Step 4: Create Deployment Script

Create a deployment script at `/opt/deployment/deploy-PROJECT_NAME.sh` on the remote server:

```bash
ssh mark@100.79.70.15
sudo nano /opt/deployment/deploy-PROJECT_NAME.sh
```

Use this template:

```bash
#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
REPO_URL="http://100.79.70.15:3000/mark/PROJECT_NAME.git"
DEPLOY_DIR="/opt/PROJECT_NAME"
BACKUP_DIR="/opt/backups/PROJECT_NAME"
BRANCH="main"
CONTAINER_NAME="PROJECT_NAME"

# Backup function
backup() {
    log "Creating backup..."
    mkdir -p "$BACKUP_DIR"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)

    if [ -d "$DEPLOY_DIR" ]; then
        tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" -C "$DEPLOY_DIR" . 2>/dev/null || true
        log "Backup created: backup_$TIMESTAMP.tar.gz"

        # Keep only last 5 backups
        cd "$BACKUP_DIR" && ls -t backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm
    fi
}

# Deploy function
deploy() {
    log "Starting deployment for PROJECT_NAME..."

    # Clone or pull
    if [ ! -d "$DEPLOY_DIR/.git" ]; then
        log "Cloning repository..."
        git clone "$REPO_URL" "$DEPLOY_DIR"
        cd "$DEPLOY_DIR"
    else
        cd "$DEPLOY_DIR"
        log "Pulling latest changes..."
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
    fi

    COMMIT_HASH=$(git rev-parse --short HEAD)
    log "Deploying commit: $COMMIT_HASH"

    # Deploy with Docker Compose
    log "Building and restarting containers..."
    docker compose down || true
    docker compose build --no-cache
    docker compose up -d

    log "✓ Deployment successful!"
}

# Main
case "${1:-deploy}" in
    deploy)
        backup
        deploy
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
        ;;
    *)
        echo "Usage: $0 {deploy|backup|logs|status}"
        exit 1
        ;;
esac
```

Make it executable:
```bash
sudo chmod +x /opt/deployment/deploy-PROJECT_NAME.sh
```

### Step 5: Setup Webhook (Optional - for Auto-Deploy)

1. Go to your repository in Gitea: `http://100.79.70.15:3000/mark/PROJECT_NAME`
2. Go to Settings → Webhooks → Add Webhook → Gitea
3. Configure:
   - **Target URL**: `http://webhook-server:9000/webhook`
   - **HTTP Method**: POST
   - **POST Content Type**: application/json
   - **Secret**: `98abd84808c394303be92699dfe7a4468747636986754a2c31d66609e8cc85a0`
   - **Trigger On**: Push events
   - **Branch filter**: `main`

4. Update webhook server to handle multiple projects:
   - Edit `/opt/deployment/webhook-server.py` to route to appropriate deployment script
   - Or create project-specific webhook endpoints

### Step 6: Test Deployment

**Manual deployment:**
```bash
ssh mark@100.79.70.15 "/opt/deployment/deploy-PROJECT_NAME.sh deploy"
```

**Automatic (via webhook):**
```bash
git add .
git commit -m "Test deployment"
git push gitea main
```

## Project-Specific Webhook Server

For multiple projects, you can extend the webhook server to handle different repositories:

```python
# In webhook-server.py, add this to the webhook() function:

@app.route('/webhook', methods=['POST'])
def webhook():
    # ... existing verification code ...

    payload = request.json
    repo_name = payload.get('repository', {}).get('name', '')

    # Map repositories to deployment scripts
    deploy_scripts = {
        'transcriber': '/opt/deployment/deploy.sh',
        'PROJECT_NAME': '/opt/deployment/deploy-PROJECT_NAME.sh',
        # Add more projects here
    }

    deploy_script = deploy_scripts.get(repo_name)
    if not deploy_script:
        logger.warning(f"No deployment script for repo: {repo_name}")
        return jsonify({'message': 'Repository not configured for deployment'}), 200

    # ... rest of deployment logic using deploy_script ...
```

## Directory Structure

```
/opt/
├── whisper-app/              # First project (transcriber)
├── PROJECT_NAME/             # Your new project
├── deployment/
│   ├── deploy.sh             # Whisper/Transcriber deployment
│   ├── deploy-PROJECT_NAME.sh # New project deployment
│   ├── webhook-server.py     # Webhook receiver
│   └── docker-compose.webhook.yml
├── backups/
│   ├── whisper-app/          # Transcriber backups
│   └── PROJECT_NAME/         # New project backups
└── gitea/                    # Gitea data
```

## Example: Adding a Second Project

Let's say you want to add a project called "my-web-app":

```bash
# 1. Create repository via API
curl -X POST -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  -H "Content-Type: application/json" \
  http://100.79.70.15:3000/api/v1/user/repos \
  -d '{"name":"my-web-app","private":true}'

# 2. Add remote locally
cd /d/Code/my-web-app
git remote add gitea http://100.79.70.15:3000/mark/my-web-app.git

# 3. Create deployment script on remote
ssh mark@100.79.70.15 "sudo tee /opt/deployment/deploy-my-web-app.sh" << 'EOF'
#!/bin/bash
set -e
# ... (use template above, replace PROJECT_NAME with my-web-app) ...
EOF

# 4. Make executable
ssh mark@100.79.70.15 "sudo chmod +x /opt/deployment/deploy-my-web-app.sh"

# 5. Test deployment
ssh mark@100.79.70.15 "/opt/deployment/deploy-my-web-app.sh deploy"
```

## Managing Multiple Projects

### List all your repositories:
```bash
curl -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  http://100.79.70.15:3000/api/v1/user/repos | jq '.[].name'
```

### Deploy all projects:
```bash
#!/bin/bash
# deploy-all.sh
for script in /opt/deployment/deploy-*.sh; do
    echo "Deploying: $script"
    $script deploy
done
```

### Check status of all projects:
```bash
#!/bin/bash
# status-all.sh
for script in /opt/deployment/deploy-*.sh; do
    echo "Status: $script"
    $script status
done
```

## Gitea API Reference

Full API documentation: http://100.79.70.15:3000/api/swagger

Common operations:

```bash
# List all repos
curl -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  http://100.79.70.15:3000/api/v1/user/repos

# Get repo details
curl -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  http://100.79.70.15:3000/api/v1/repos/mark/PROJECT_NAME

# Create webhook via API
curl -X POST -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  -H "Content-Type: application/json" \
  http://100.79.70.15:3000/api/v1/repos/mark/PROJECT_NAME/hooks \
  -d '{
    "type": "gitea",
    "config": {
      "url": "http://webhook-server:9000/webhook",
      "content_type": "json",
      "secret": "98abd84808c394303be92699dfe7a4468747636986754a2c31d66609e8cc85a0"
    },
    "events": ["push"],
    "active": true
  }'
```

## Security Best Practices

1. **Rotate tokens periodically**: Generate new API tokens every few months
2. **Use repository-specific deploy keys**: For production, use read-only deploy keys instead of personal tokens
3. **Limit webhook access**: Configure webhook firewall rules to only accept from Gitea IP
4. **Use HTTPS**: Set up SSL/TLS for Gitea in production

## Troubleshooting

### Push fails with authentication error
```bash
# Update stored credentials
git config credential.helper store
git push gitea main
# Enter: mark / 97a9a761c190eca3936449cf6af9f03a3b78daef
```

### Deployment script not found
```bash
# Check if script exists
ssh mark@100.79.70.15 "ls -la /opt/deployment/deploy-*.sh"

# Fix permissions
ssh mark@100.79.70.15 "sudo chmod +x /opt/deployment/deploy-*.sh"
```

### Repository not deploying automatically
```bash
# Check webhook status
curl -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  http://100.79.70.15:3000/api/v1/repos/mark/PROJECT_NAME/hooks

# Test webhook manually
curl -X POST http://100.79.70.15:9000/webhook \
  -H "X-Gitea-Event: push" \
  -H "Content-Type: application/json" \
  -d '{"repository":{"name":"PROJECT_NAME"},"ref":"refs/heads/main"}'
```

---

**Need help?** Check the main [CICD-SUMMARY.md](CICD-SUMMARY.md) or [DEPLOYMENT.md](DEPLOYMENT.md) for more details.
