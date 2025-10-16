# Remote Gitea Deployment Guide

This guide shows you how to deploy Gitea to a remote server from your local machine.

## 🎯 Prerequisites

- **Remote Server Requirements:**
  - Linux server (Ubuntu/Debian/CentOS/etc.)
  - Docker and Docker Compose installed
  - SSH access with sudo privileges
  - Ports 3000, 2222, 9000 available

- **Local Machine Requirements:**
  - SSH client
  - OpenSSL (for generating secrets)

## 🚀 Quick Remote Setup

### Method 1: Automated Script (Easiest)

```bash
cd deployment
./remote-setup.sh
```

The script will:
1. Prompt for server details (IP, username, SSH port)
2. Test SSH connection
3. Check Docker installation
4. Generate secure credentials
5. Copy and configure files
6. Start Gitea on remote server

### Method 2: Manual Remote Setup

#### Step 1: Prepare the remote server

SSH into your server:
```bash
ssh user@your-server-ip
```

Install Docker if needed:
```bash
# For Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

Create deployment directory:
```bash
sudo mkdir -p /opt/gitea
sudo chown $USER:$USER /opt/gitea
```

#### Step 2: Copy files from local machine

From your local machine (in the deployment folder):
```bash
# Set your server details
REMOTE_HOST="your-server-ip"
REMOTE_USER="your-username"

# Copy deployment files
scp -r ./* $REMOTE_USER@$REMOTE_HOST:/opt/gitea/
```

#### Step 3: Configure on remote server

SSH back into your server:
```bash
ssh $REMOTE_USER@$REMOTE_HOST
cd /opt/gitea
```

Generate secure passwords:
```bash
DB_PASSWORD=$(openssl rand -hex 16)
WEBHOOK_SECRET=$(openssl rand -hex 32)

# Save to .env
cat > .env << EOF
WEBHOOK_SECRET=$WEBHOOK_SECRET
DB_PASSWORD=$DB_PASSWORD
EOF

echo "Save these credentials:"
echo "DB Password: $DB_PASSWORD"
echo "Webhook Secret: $WEBHOOK_SECRET"
```

Update docker-compose.gitea.yml:
```bash
# Get your server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Edit the file
nano docker-compose.gitea.yml

# Update these lines:
# - GITEA__database__PASSWD=YOUR_DB_PASSWORD
# - GITEA__server__DOMAIN=YOUR_SERVER_IP
# - GITEA__server__ROOT_URL=http://YOUR_SERVER_IP:3000/
```

#### Step 4: Start Gitea

```bash
docker compose -f docker-compose.gitea.yml up -d
```

Check status:
```bash
docker compose -f docker-compose.gitea.yml ps
docker compose -f docker-compose.gitea.yml logs -f
```

### Method 3: Docker Context (Advanced)

You can control remote Docker from your local machine using Docker contexts:

```bash
# Create a Docker context for remote server
docker context create remote-server \
  --docker "host=ssh://user@your-server-ip"

# Use the remote context
docker context use remote-server

# Now all docker commands run on remote server
cd deployment
docker compose -f docker-compose.gitea.yml up -d

# Switch back to local
docker context use default
```

## 🔐 SSH Key Setup (Recommended)

For easier remote deployment, set up SSH key authentication:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your@email.com"

# Copy to remote server
ssh-copy-id user@your-server-ip

# Test passwordless login
ssh user@your-server-ip
```

## 🔒 Firewall Configuration

On your remote server, open required ports:

### Ubuntu/Debian (UFW)
```bash
sudo ufw allow 3000/tcp   # Gitea Web
sudo ufw allow 2222/tcp   # Gitea SSH
sudo ufw allow 9000/tcp   # Webhook (optional, can restrict to specific IPs)
sudo ufw allow 22/tcp     # SSH
sudo ufw enable
```

### CentOS/RHEL (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=2222/tcp
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

### Using iptables
```bash
sudo iptables -A INPUT -p tcp --dport 3000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 2222 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 9000 -j ACCEPT
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

## 🌐 Domain Setup (Optional but Recommended)

### Using a Domain Name

1. **Point your domain to server:**
   - Create an A record: `git.yourdomain.com` → `your-server-ip`

2. **Update Gitea configuration:**
   ```bash
   # Edit docker-compose.gitea.yml
   GITEA__server__DOMAIN=git.yourdomain.com
   GITEA__server__ROOT_URL=http://git.yourdomain.com:3000/
   ```

3. **Set up reverse proxy with SSL (recommended):**

Create `nginx.conf`:
```nginx
server {
    listen 80;
    server_name git.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Install Certbot for free SSL:
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d git.yourdomain.com
```

## 📊 Monitoring Remote Deployment

### View logs from local machine:
```bash
ssh user@your-server-ip "cd /opt/gitea && docker compose logs -f"
```

### Check status:
```bash
ssh user@your-server-ip "cd /opt/gitea && docker compose ps"
```

### Monitor with watch:
```bash
ssh user@your-server-ip "watch -n 5 docker ps"
```

## 🔄 Remote Deployment Workflow

After Gitea is running on your remote server:

1. **Complete Gitea setup:**
   - Open `http://your-server-ip:3000`
   - Complete wizard
   - Create admin account

2. **Push your code to Gitea:**
   ```bash
   git remote add origin http://your-server-ip:3000/username/whisper.git
   git push -u origin main
   ```

3. **Set up webhook deployment:**
   - Option A: Deploy webhook server on same remote server
   - Option B: Deploy webhook server on application server
   - Configure webhook in Gitea repository settings

## 🛠️ Troubleshooting Remote Deployment

### Can't connect to remote server
```bash
# Test connection
ping your-server-ip

# Test SSH
ssh -v user@your-server-ip

# Check firewall
ssh user@your-server-ip "sudo ufw status"
```

### Docker permission denied
```bash
# Add user to docker group
ssh user@your-server-ip "sudo usermod -aG docker $USER"

# Re-login
ssh user@your-server-ip
```

### Can't access Gitea web UI
```bash
# Check if container is running
ssh user@your-server-ip "docker ps | grep gitea"

# Check logs
ssh user@your-server-ip "docker logs gitea"

# Check firewall
ssh user@your-server-ip "sudo netstat -tlnp | grep 3000"
```

### Port already in use
```bash
# Find what's using the port
ssh user@your-server-ip "sudo lsof -i :3000"

# Change port in docker-compose.yml
# Change: "3000:3000" to "3001:3000"
```

## 🔐 Security Best Practices

1. **Use SSH keys instead of passwords**
2. **Change default SSH port:**
   ```bash
   # Edit /etc/ssh/sshd_config
   Port 2222
   ```

3. **Disable root SSH login:**
   ```bash
   PermitRootLogin no
   ```

4. **Enable automatic security updates:**
   ```bash
   sudo apt-get install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

5. **Use strong passwords for Gitea database**

6. **Set up fail2ban:**
   ```bash
   sudo apt-get install fail2ban
   sudo systemctl enable fail2ban
   ```

## 📦 Backup Remote Gitea

Create backup script on remote server:
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/gitea"
mkdir -p $BACKUP_DIR

# Backup Gitea data
docker exec gitea sh -c 'cd /data && tar czf - .' > \
  $BACKUP_DIR/gitea-data-$(date +%Y%m%d).tar.gz

# Backup database
docker exec gitea-db pg_dump -U gitea gitea | \
  gzip > $BACKUP_DIR/gitea-db-$(date +%Y%m%d).sql.gz

# Keep only last 7 backups
find $BACKUP_DIR -name "gitea-*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "gitea-*.sql.gz" -mtime +7 -delete
```

Set up automatic backups with cron:
```bash
# Add to crontab
0 2 * * * /opt/gitea/backup.sh
```

## 🎉 Done!

Your Gitea is now running on a remote server. You can:
- Access it from anywhere: `http://your-server-ip:3000`
- Push/pull code remotely
- Set up automatic deployment

Next step: Configure webhook deployment (see main DEPLOYMENT.md)
