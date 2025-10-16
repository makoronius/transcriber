# Deployment Setup

This folder contains everything you need to set up self-hosted Git (Gitea) and automatic deployment for your Whisper application.

## 🚀 Quick Start

### Local Setup (Gitea on this machine)

```bash
cd deployment
chmod +x quick-start.sh
./quick-start.sh
```

The interactive wizard will guide you through:
- Setting up Gitea (self-hosted Git server)
- Configuring webhook-based deployment
- Setting up Git remote

### Remote Setup (Gitea on remote server)

```bash
cd deployment
chmod +x remote-setup.sh
./remote-setup.sh
```

This will deploy Gitea to your remote server via SSH. See [REMOTE-SETUP.md](REMOTE-SETUP.md) for details.

### Manual Setup

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed step-by-step instructions.

## 📁 Files Overview

| File | Purpose |
|------|---------|
| `quick-start.sh` | Interactive setup wizard (local) |
| `remote-setup.sh` | Remote deployment script (deploy to server) |
| `docker-compose.gitea.yml` | Gitea server configuration |
| `docker-compose.webhook.yml` | Webhook server for auto-deployment |
| `deploy.sh` | Deployment script (runs on target host) |
| `webhook-server.py` | Webhook receiver and deployment trigger |
| `DEPLOYMENT.md` | Complete documentation |
| `REMOTE-SETUP.md` | Remote server deployment guide |

## 🎯 What You'll Get

1. **Gitea** - Your own private Git server with web UI
   - Access at: `http://your-server:3000`
   - Git operations via HTTP or SSH
   - Built-in CI/CD with Gitea Actions

2. **Automatic Deployment** - Push code and it deploys automatically
   - Push to main branch → triggers webhook → deploys to Docker host
   - Includes rollback capability
   - Automated backups

3. **Full Control** - Everything runs on your infrastructure
   - No reliance on GitHub/GitLab
   - Your code stays private
   - Free and open source

## 🔧 Requirements

- Docker & Docker Compose installed
- A server/PC to host Gitea (can be Windows/Linux)
- Port 3000 (Gitea Web), 2222 (Git SSH), 9000 (Webhook) available

## 📖 Documentation

- **[QUICK-REFERENCE.md](QUICK-REFERENCE.md)** - Quick reference card with commands and credentials
- **[ADDING-PROJECTS.md](ADDING-PROJECTS.md)** - How to add new projects to CI/CD
- **[CICD-SUMMARY.md](CICD-SUMMARY.md)** - Complete CI/CD setup overview
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Detailed deployment guide
- **[REMOTE-SETUP.md](REMOTE-SETUP.md)** - Remote server setup instructions

## 💡 Deployment Options

### Option 1: Webhook-based (Recommended)
- Push code → Webhook triggers → Auto-deploy
- Simple and reliable
- No need to configure runners

### Option 2: Gitea Actions (Advanced)
- GitHub Actions compatible
- More flexibility
- Requires runner setup

### Option 3: Manual
```bash
/opt/deployment/deploy.sh deploy
```

## 🔐 Security Notes

Before going to production:
1. Change default passwords in docker-compose files
2. Use strong webhook secret (generated automatically)
3. Set up HTTPS with reverse proxy
4. Configure firewall rules

## 🆘 Need Help?

1. Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
2. Verify services are running: `docker compose ps`
3. Check logs: `docker compose logs -f`

## 🔄 Typical Workflow

```bash
# 1. Make changes
vim web_app.py

# 2. Commit
git add .
git commit -m "Update feature"

# 3. Push to Gitea (triggers auto-deployment)
git push origin main

# 4. Check deployment
# Webhook automatically deploys to your Docker host
```

That's it! 🎉
