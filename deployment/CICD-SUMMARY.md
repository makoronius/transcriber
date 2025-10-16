# CI/CD Setup Summary

## ✅ What's Working

### 1. **Portainer** - Docker Management UI
- **URL**: `https://100.79.70.15:9443`
- **Status**: ✅ Running
- **Purpose**: Visual Docker container management

### 2. **Gitea** - Self-Hosted Git Server
- **URL**: `http://100.79.70.15:3000`
- **Status**: ✅ Running
- **Repository**: `http://100.79.70.15:3000/mark/transcriber`
- **Credentials**:
  - Username: `mark`
  - Password: `Admin123!`
- **Access Token**: `ee1aecdc16ac139c5ed0c5e68e6663c7cb071411`

### 3. **Webhook Server** - Event Listener
- **URL**: `http://100.79.70.15:9000`
- **Status**: ✅ Running & Receiving Events
- **Webhook Secret**: `98abd84808c394303be92699dfe7a4468747636986754a2c31d66609e8cc85a0`
- **Functionality**: Successfully receives push events from Gitea

### 4. **Code Repository**
- **Location**: `/opt/whisper-app` (on remote server)
- **Remote**: Gitea (`gitea` remote in local repository)
- **Status**: ✅ Cloned and ready

### 5. **Deployment Script**
- **Location**: `/opt/deployment/deploy.sh`
- **Status**: ✅ Ready to use
- **Purpose**: Automated deployment with Docker

## 📋 Current Deployment Workflow

### Automatic (Webhook - NOW WORKING! ✅)
When you push to Gitea, the webhook server **automatically receives the notification and deploys your changes** ✅

The webhook container uses SSH to trigger the deployment script on the host, which:
- Pulls latest code from Gitea
- Backs up existing configuration
- Rebuilds and restarts Docker containers
- Verifies deployment health

**Just push to Gitea and your changes will be deployed automatically!**

### Manual Deployment (Alternative Option)

When you want to deploy changes:

```bash
# From your local machine, trigger deployment on remote server
ssh mark@100.79.70.15 "/opt/deployment/deploy.sh deploy"
```

Or on the remote server directly:
```bash
/opt/deployment/deploy.sh deploy
```

### Deployment Script Commands

```bash
# Deploy latest code
/opt/deployment/deploy.sh deploy

# Rollback to previous version
/opt/deployment/deploy.sh rollback

# Create backup
/opt/deployment/deploy.sh backup

# View logs
/opt/deployment/deploy.sh logs

# Check status
/opt/deployment/deploy.sh status
```

## 🔄 Complete Workflow Example

1. **Make changes locally:**
   ```bash
   cd /d/Code/whisper
   # Make your changes
   git add .
   git commit -m "Your changes"
   ```

2. **Push to Gitea:**
   ```bash
   git push gitea main
   ```
   ✅ Webhook automatically notifies the server

3. **Deploy (manual trigger):**
   ```bash
   ssh mark@100.79.70.15 "/opt/deployment/deploy.sh deploy"
   ```

4. **Verify deployment:**
   - Check via Portainer: `https://100.79.70.15:9443`
   - Or check logs: `ssh mark@100.79.70.15 "docker logs whisper-transcriber"`

## 🎯 Directori

es on Remote Server

| Directory | Purpose |
|-----------|---------|
| `/opt/whisper-app` | Deployed application code |
| `/opt/deployment` | Deployment scripts and webhook |
| `/opt/backups` | Automatic backups (last 5 kept) |
| `/opt/gitea` | Gitea configuration (if moved) |

## 🔐 Important Credentials

### Gitea
- **URL**: `http://100.79.70.15:3000`
- **Username**: `mark`
- **Password**: `Admin123!` ⚠️ Change this!
- **API Tokens**:
  - **Push Token**: `ee1aecdc16ac139c5ed0c5e68e6663c7cb071411` (for git push)
  - **Development Token**: `97a9a761c190eca3936449cf6af9f03a3b78daef` (API access, full scope)

### Webhook
- **Secret**: `98abd84808c394303be92699dfe7a4468747636986754a2c31d66609e8cc85a0`

### Portainer
- Set up on first access at `https://100.79.70.15:9443`

## 📝 Git Remotes

```bash
# View remotes
git remote -v

# Push to GitHub
git push origin main

# Push to Gitea
git push gitea main

# Push to both
git push origin main && git push gitea main
```

## 🛠️ Troubleshooting

### Check if services are running
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

## 🚀 Future Enhancements

To enable fully automatic deployment from webhook:
1. Configure webhook container to execute host commands via SSH
2. Or use Gitea Actions (GitHub Actions compatible)
3. Or set up a deployment key for secure automation

## 📚 Documentation Files

- `DEPLOYMENT.md` - Complete deployment guide
- `REMOTE-SETUP.md` - Remote server setup guide
- `ADDING-PROJECTS.md` - Guide for adding new projects to CI/CD
- `README.md` - Quick reference

## ✨ What You've Built

You now have:
- ✅ Self-hosted private Git server (Gitea)
- ✅ Docker container management UI (Portainer)
- ✅ Webhook notifications on code push
- ✅ Deployment scripts ready to use
- ✅ Backup system (automatic)
- ✅ Rollback capability
- ✅ Full control over your infrastructure

**No dependency on GitHub, GitLab, or any third-party CI/CD service!**

---

**Need help?** Check the troubleshooting section or the detailed guides in the `deployment/` folder.
