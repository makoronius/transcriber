# Docker Setup for Whisper AI Transcriber

This guide will help you run the Whisper AI Transcriber in a Docker container on WSL.

## Prerequisites

### 1. Install Docker on WSL
```bash
# Update packages
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Install NVIDIA Container Toolkit (For GPU Support)

If you have an NVIDIA GPU and want GPU acceleration:

```bash
# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install NVIDIA Container Toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 3. Verify GPU Access (Optional)
```bash
# Test NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

## Building and Running

### Option 1: Using Docker Compose (Recommended)

1. **Navigate to the project directory**
   ```bash
   cd /mnt/d/Code/whisper
   ```

2. **Create environment file (optional)**
   ```bash
   echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
   ```

3. **Build and start the container**
   ```bash
   # With GPU support
   docker compose up -d --build

   # Without GPU (edit docker-compose.yml first - comment out deploy section)
   docker compose up -d --build
   ```

4. **View logs**
   ```bash
   docker compose logs -f
   ```

5. **Access the web interface**
   Open your browser and navigate to: `http://localhost:5000`

### Option 2: Using Docker CLI

1. **Build the image**
   ```bash
   docker build -t whisper-transcriber .
   ```

2. **Run the container**
   ```bash
   # With GPU
   docker run -d \
     --name whisper-transcriber \
     --gpus all \
     -p 5000:5000 \
     -v $(pwd)/yt_downloads:/app/yt_downloads \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/logs:/app/logs \
     -v $(pwd)/config.yaml:/app/config.yaml \
     -v $(pwd)/whisper_jobs.db:/app/whisper_jobs.db \
     --restart unless-stopped \
     whisper-transcriber

   # Without GPU
   docker run -d \
     --name whisper-transcriber \
     -p 5000:5000 \
     -v $(pwd)/yt_downloads:/app/yt_downloads \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/logs:/app/logs \
     -v $(pwd)/config.yaml:/app/config.yaml \
     -v $(pwd)/whisper_jobs.db:/app/whisper_jobs.db \
     --restart unless-stopped \
     whisper-transcriber
   ```

## Managing the Container

### View Container Status
```bash
docker compose ps
# or
docker ps
```

### View Logs
```bash
# Follow logs in real-time
docker compose logs -f

# View last 100 lines
docker compose logs --tail=100

# View logs for specific service
docker compose logs whisper-web
```

### Stop the Container
```bash
docker compose stop
# or
docker stop whisper-transcriber
```

### Start the Container
```bash
docker compose start
# or
docker start whisper-transcriber
```

### Restart the Container
```bash
docker compose restart
# or
docker restart whisper-transcriber
```

### Stop and Remove
```bash
docker compose down
# or
docker stop whisper-transcriber && docker rm whisper-transcriber
```

### Execute Commands Inside Container
```bash
# Open a shell
docker compose exec whisper-web bash

# Run the subtitle cleanup script
docker compose exec whisper-web python srt_cleanup.py path/to/subtitle.srt

# Check GPU availability
docker compose exec whisper-web python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

## Volume Mounts Explained

The following directories are mounted as volumes:

- `./yt_downloads` - Downloaded YouTube videos and subtitles
- `./uploads` - Uploaded files for transcription
- `./logs` - Application logs
- `./backups` - Backup files
- `./config.yaml` - Configuration file
- `./youtube_cookies.txt` - YouTube cookies (read-only)
- `./whisper_jobs.db` - SQLite database

This means your data persists even if you remove and recreate the container.

## Updating the Application

### Update Code and Rebuild
```bash
# Pull latest changes (if using git)
git pull

# Rebuild and restart
docker compose up -d --build
```

### Update Dependencies
If you modify `requirements.txt`:
```bash
docker compose build --no-cache
docker compose up -d
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker compose logs

# Check if port is already in use
sudo netstat -tulpn | grep :5000
```

### GPU Not Detected
```bash
# Verify NVIDIA runtime is configured
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# Check Docker daemon configuration
cat /etc/docker/daemon.json
```

### Permission Issues with Volumes
```bash
# Fix ownership (from WSL)
sudo chown -R $USER:$USER yt_downloads uploads logs backups
```

### Out of Disk Space
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Remove unused images
docker image prune -a
```

### Container Uses Too Much Memory
Edit `docker-compose.yml` and uncomment resource limits:
```yaml
mem_limit: 16g
cpus: 8
```

## Performance Tips

1. **GPU Memory**: For large models, ensure you have enough GPU memory (at least 8GB VRAM for large-v3)

2. **CPU Fallback**: If you don't have a GPU, modify `config.yaml`:
   ```yaml
   transcription:
     device: cpu
     compute: int8
   ```

3. **Model Selection**: Use smaller models for faster processing:
   ```yaml
   transcription:
     model: medium  # or small, base, tiny
   ```

## Production Deployment

For production use, consider:

1. **Use a reverse proxy** (nginx) - uncomment nginx section in docker-compose.yml
2. **Set up SSL/TLS** with Let's Encrypt
3. **Configure firewall** to restrict access
4. **Set strong SECRET_KEY** in .env file
5. **Regular backups** of database and downloads
6. **Monitor logs** and set up log rotation

## Accessing from Windows

Since you're running Docker in WSL, you can access the application from Windows at:
- `http://localhost:5000`
- `http://127.0.0.1:5000`
- `http://<your-wsl-ip>:5000`

To find your WSL IP:
```bash
ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1
```

## Notes for WSL

- Docker containers in WSL can access Windows files mounted at `/mnt/c/`, `/mnt/d/`, etc.
- The project is currently at `/mnt/d/Code/whisper`
- Make sure Docker Desktop is running on Windows if you're using Docker Desktop
- Alternatively, use Docker installed directly in WSL (recommended for better performance)
