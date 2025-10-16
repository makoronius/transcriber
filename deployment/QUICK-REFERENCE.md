# CI/CD Quick Reference Card

## 🔑 Credentials

**Gitea**: http://100.79.70.15:3000
- Username: `mark` / Password: `Admin123!`
- Push Token: `ee1aecdc16ac139c5ed0c5e68e6663c7cb071411`
- **Development API Token**: `97a9a761c190eca3936449cf6af9f03a3b78daef`

**Portainer**: https://100.79.70.15:9443

**Webhook Secret**: `98abd84808c394303be92699dfe7a4468747636986754a2c31d66609e8cc85a0`

---

## 🚀 Common Commands

### Deploy Transcriber Project
```bash
# Manual deployment
ssh mark@100.79.70.15 "/opt/deployment/deploy.sh deploy"

# Check status
ssh mark@100.79.70.15 "/opt/deployment/deploy.sh status"

# View logs
ssh mark@100.79.70.15 "/opt/deployment/deploy.sh logs"

# Rollback
ssh mark@100.79.70.15 "/opt/deployment/deploy.sh rollback"
```

### Add New Project
```bash
cd /d/Code/your-project
/d/Code/whisper/deployment/add-project.sh PROJECT_NAME [PORT]

# Example:
/d/Code/whisper/deployment/add-project.sh my-web-app 5001
```

### Git Operations
```bash
# Push to Gitea (triggers auto-deploy)
git push gitea main

# Push to both GitHub and Gitea
git push origin main && git push gitea main

# View remotes
git remote -v
```

### Gitea API
```bash
# List all repositories
curl -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  http://100.79.70.15:3000/api/v1/user/repos

# Create repository
curl -X POST -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  -H "Content-Type: application/json" \
  http://100.79.70.15:3000/api/v1/user/repos \
  -d '{"name":"PROJECT_NAME","private":true}'

# List webhooks for a repo
curl -H "Authorization: token 97a9a761c190eca3936449cf6af9f03a3b78daef" \
  http://100.79.70.15:3000/api/v1/repos/mark/PROJECT_NAME/hooks
```

---

## 📁 Directory Structure on Remote

```
/opt/
├── whisper-app/              # Transcriber application
├── deployment/
│   ├── deploy.sh             # Transcriber deployment script
│   ├── deploy-*.sh           # Other project deployment scripts
│   ├── webhook-server.py     # Webhook receiver
│   └── docker-compose.webhook.yml
├── backups/
│   ├── whisper-app/
│   └── [other-projects]/
└── gitea/
```

---

## 🔧 Troubleshooting

### Check service status
```bash
ssh mark@100.79.70.15 "docker ps"
```

### View webhook logs
```bash
ssh mark@100.79.70.15 "docker logs webhook-server --tail 50"
```

### View Gitea logs
```bash
ssh mark@100.79.70.15 "docker logs gitea --tail 50"
```

### Restart services
```bash
# Restart Gitea
ssh mark@100.79.70.15 "cd /home/mark/gitea && docker compose restart"

# Restart webhook
ssh mark@100.79.70.15 "cd /opt/deployment && docker compose restart"
```

### Update port proxy on Windows
```powershell
# On remote Windows host (run as Administrator)
wsl cat ~/Update-DockerPortProxy.ps1 | powershell -
```

### Fix git credentials
```bash
# Store credentials for push
git config credential.helper store
git push gitea main
# Username: mark
# Password: ee1aecdc16ac139c5ed0c5e68e6663c7cb071411
```

---

## 📖 Documentation

- **[CICD-SUMMARY.md](CICD-SUMMARY.md)** - Complete CI/CD overview
- **[ADDING-PROJECTS.md](ADDING-PROJECTS.md)** - Add new projects guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Detailed deployment instructions
- **[REMOTE-SETUP.md](REMOTE-SETUP.md)** - Remote server setup

---

## 🎯 Typical Workflow

```bash
# 1. Make changes
cd /d/Code/whisper
vim web_app.py

# 2. Commit
git add .
git commit -m "Your changes"

# 3. Push to Gitea (auto-deploys)
git push gitea main

# 4. Optionally push to GitHub
git push origin main

# 5. Verify deployment
ssh mark@100.79.70.15 "/opt/deployment/deploy.sh status"
```

---

## 🆘 Emergency Commands

### Stop all containers
```bash
ssh mark@100.79.70.15 "docker stop \$(docker ps -q)"
```

### View all running containers
```bash
ssh mark@100.79.70.15 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

### Check disk space
```bash
ssh mark@100.79.70.15 "df -h /opt"
```

### Clean up old Docker images
```bash
ssh mark@100.79.70.15 "docker image prune -a -f"
```

### Restore from backup
```bash
# List backups
ssh mark@100.79.70.15 "ls -lh /opt/backups/whisper-app/"

# Restore specific backup
ssh mark@100.79.70.15 "tar -xzf /opt/backups/whisper-app/backup_TIMESTAMP.tar.gz -C /opt/whisper-app"
```

---

**Last Updated**: 2025-10-16
**Remote Server**: 100.79.70.15
**User**: mark
