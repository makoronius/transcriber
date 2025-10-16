# Self-Hosted Git + CI/CD Deployment Guide

This guide will help you set up Gitea (self-hosted Git) and automatic deployment for the Whisper transcription application.

## 🏗️ Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Your PC       │      │   Gitea Server   │      │  Deploy Target  │
│   (Development) │─────▶│   (Git + CI/CD)  │─────▶│  (Docker Host)  │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                              │
                              ├─ Gitea Web UI (Port 3000)
                              ├─ Gitea SSH (Port 2222)
                              └─ Webhook Server (Port 9000)
```

## 📋 Prerequisites

- Docker and Docker Compose installed
- A server/PC to host Gitea
- A server/PC to deploy the whisper app (can be the same machine)

## 🚀 Setup Steps

### Step 1: Deploy Gitea

1. **Navigate to deployment directory:**
   ```bash
   cd deployment
   ```

2. **Edit the Gitea configuration:**
   Open `docker-compose.gitea.yml` and update:
   - `GITEA__database__PASSWD` - Change to a secure password
   - `GITEA__server__DOMAIN` - Your server's domain or IP
   - `GITEA__server__ROOT_URL` - Full URL (e.g., http://192.168.1.100:3000/)

3. **Start Gitea:**
   ```bash
   docker compose -f docker-compose.gitea.yml up -d
   ```

4. **Access Gitea Web UI:**
   - Open browser: `http://your-server-ip:3000`
   - Complete the initial setup wizard
   - Create an admin account

5. **Get Gitea Actions Runner Token:**
   - Login to Gitea
   - Go to Site Administration → Actions → Runners
   - Click "Create new Runner"
   - Copy the registration token

6. **Configure the runner:**
   - Edit `docker-compose.gitea.yml`
   - Update `GITEA_RUNNER_REGISTRATION_TOKEN` with your token
   - Restart: `docker compose -f docker-compose.gitea.yml restart gitea-runner`

### Step 2: Push Your Code to Gitea

1. **Create a new repository in Gitea:**
   - Click "+" → "New Repository"
   - Name it (e.g., "whisper")
   - Click "Create Repository"

2. **Update your local git remote:**
   ```bash
   # Remove GitHub remote (optional)
   git remote remove origin

   # Add Gitea remote
   git remote add origin http://your-gitea-server:3000/your-username/whisper.git

   # Push code
   git push -u origin main
   ```

### Step 3: Setup Webhook Deployment (Option A - Recommended)

This method automatically deploys when you push to Gitea.

1. **Generate a webhook secret:**
   ```bash
   openssl rand -hex 32
   ```

2. **Create environment file:**
   ```bash
   cd deployment
   cat > .env << EOF
   WEBHOOK_SECRET=your-generated-secret-here
   EOF
   ```

3. **Update webhook configuration:**
   Edit `docker-compose.webhook.yml`:
   - Update `REPO_URL` with your Gitea repository URL
   - Update `DEPLOY_DIR` where you want to deploy

4. **Start webhook server:**
   ```bash
   docker compose -f docker-compose.webhook.yml up -d
   ```

5. **Configure webhook in Gitea:**
   - Go to your repository → Settings → Webhooks
   - Click "Add Webhook" → "Gitea"
   - Payload URL: `http://webhook-server:9000/webhook`
   - Secret: Use the secret from step 1
   - Events: Select "Push"
   - Click "Add Webhook"

### Step 4: Setup Deployment Target

On the machine where you want to deploy the whisper app:

1. **Copy deployment script:**
   ```bash
   sudo mkdir -p /opt/deployment
   sudo cp deployment/deploy.sh /opt/deployment/
   sudo chmod +x /opt/deployment/deploy.sh
   ```

2. **Configure deployment:**
   Edit `/opt/deployment/deploy.sh` and update:
   - `REPO_URL` - Your Gitea repository URL
   - `DEPLOY_DIR` - Where to deploy (e.g., `/opt/whisper`)
   - `BRANCH` - Branch to deploy (default: main)

3. **Create deploy directory:**
   ```bash
   sudo mkdir -p /opt/whisper
   sudo chown $USER:$USER /opt/whisper
   ```

### Step 5: Test Deployment

#### Option A: Manual deployment
```bash
/opt/deployment/deploy.sh deploy
```

#### Option B: Trigger via webhook
```bash
# Push a commit
git add .
git commit -m "Test deployment"
git push origin main

# Webhook will automatically trigger deployment
```

#### Option C: Manual webhook trigger
```bash
curl -X POST http://your-server:9000/deploy \
  -H "Authorization: Bearer your-webhook-secret"
```

## 📝 Available Commands

The deployment script supports several commands:

```bash
# Deploy latest version
./deploy.sh deploy

# Rollback to previous version
./deploy.sh rollback

# Create manual backup
./deploy.sh backup

# View logs
./deploy.sh logs

# Check status
./deploy.sh status
```

## 🔐 Security Recommendations

1. **Change default passwords:**
   - Gitea database password
   - Webhook secret

2. **Use SSH for Git operations:**
   - Generate SSH key: `ssh-keygen -t ed25519 -C "your@email.com"`
   - Add to Gitea: Settings → SSH/GPG Keys
   - Use SSH URL: `git@your-server:2222:username/whisper.git`

3. **Enable HTTPS:**
   - Use a reverse proxy (nginx/traefik) with SSL certificates
   - Let's Encrypt for free SSL certificates

4. **Firewall configuration:**
   ```bash
   # Only expose necessary ports
   ufw allow 3000/tcp  # Gitea web
   ufw allow 2222/tcp  # Gitea SSH
   ufw allow 9000/tcp  # Webhook (restrict to Gitea server IP)
   ```

## 🔄 Using Gitea Actions (Alternative to Webhooks)

Instead of webhooks, you can use Gitea Actions (GitHub Actions compatible):

1. **Create `.gitea/workflows/deploy.yml`:**
   ```yaml
   name: Deploy
   on:
     push:
       branches: [main]

   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - name: Deploy via SSH
           uses: appleboy/ssh-action@v0.1.10
           with:
             host: ${{ secrets.DEPLOY_HOST }}
             username: ${{ secrets.DEPLOY_USER }}
             key: ${{ secrets.SSH_PRIVATE_KEY }}
             script: |
               cd /opt/deployment
               ./deploy.sh deploy
   ```

2. **Add secrets in Gitea:**
   - Repository → Settings → Secrets
   - Add: `DEPLOY_HOST`, `DEPLOY_USER`, `SSH_PRIVATE_KEY`

## 🐛 Troubleshooting

### Gitea won't start
```bash
# Check logs
docker compose -f docker-compose.gitea.yml logs

# Check if ports are available
netstat -tulpn | grep -E '3000|2222'
```

### Webhook not triggering
```bash
# Check webhook server logs
docker compose -f docker-compose.webhook.yml logs -f

# Test webhook manually
curl -X POST http://localhost:9000/health
```

### Deployment fails
```bash
# Check deployment logs
docker compose logs whisper-transcriber

# Verify deploy script permissions
ls -la /opt/deployment/deploy.sh

# Run manually with verbose output
bash -x /opt/deployment/deploy.sh deploy
```

### Can't push to Gitea
```bash
# Check if Gitea is accessible
curl http://your-gitea-server:3000

# Verify git remote
git remote -v

# Check SSH connection (if using SSH)
ssh -T -p 2222 git@your-gitea-server
```

## 📊 Monitoring

### View deployment logs
```bash
tail -f /var/log/webhook-deploy.log
```

### Check application health
```bash
docker inspect --format='{{.State.Health.Status}}' whisper-transcriber
```

### View application logs
```bash
docker compose logs -f whisper-transcriber
```

## 🔄 Update Workflow

Normal development workflow:

1. Make changes locally
2. Commit and push to Gitea:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```
3. Webhook automatically triggers deployment
4. Check deployment logs to verify success

## 📚 Additional Resources

- [Gitea Documentation](https://docs.gitea.io/)
- [Gitea Actions](https://docs.gitea.io/en-us/usage/actions/overview/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🎯 Next Steps

1. Set up HTTPS with reverse proxy
2. Configure automated backups
3. Set up monitoring (Prometheus + Grafana)
4. Configure email notifications
5. Add staging environment

---

**Note:** Remember to backup your data regularly and test the rollback procedure!
