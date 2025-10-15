# Installation Guide

Complete installation instructions for Whisper AI Transcriber across different platforms.

---

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
  - [Docker (Recommended)](#docker-recommended)
  - [Windows (Native)](#windows-native)
  - [Windows (WSL)](#windows-wsl)
  - [Ubuntu/Linux](#ubuntu-linux)
  - [macOS](#macos)
- [Post-Installation](#post-installation)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
- **CPU**: Multi-core processor (4+ cores recommended)
- **RAM**: 8 GB (16 GB recommended for large models)
- **Disk**: 10 GB free space minimum (50+ GB recommended for videos)
- **Internet**: For downloading videos and models

### Software Requirements
- **Python**: 3.8 - 3.12 (3.12 recommended for GPU support)
  - ⚠️ Python 3.13 not yet supported for GPU (PyTorch limitation)
- **FFmpeg**: Latest stable version
- **Git**: For cloning the repository

### Optional (Highly Recommended)
- **NVIDIA GPU**: CUDA-capable with 4+ GB VRAM
- **CUDA Toolkit**: 11.8 or 12.x
- **cuDNN**: Included with PyTorch

### Performance Comparison
| Setup | Speed | 1-hour Video |
|-------|-------|--------------|
| CPU only | Baseline | ~10-30 hours |
| GPU (8GB VRAM) | 10-50x faster | ~20-60 minutes |

---

## Installation Methods

Choose the method that best suits your environment:

### Docker (Recommended)

**Best for**: Everyone, especially beginners and production deployments

**Advantages**:
- ✅ No dependency conflicts
- ✅ Consistent environment
- ✅ Easy cleanup
- ✅ Works on all platforms

See [Docker Setup Guide](DOCKER_SETUP.md) for complete instructions.

**Quick Start**:
```bash
# Clone repository
git clone https://github.com/makoronius/transcriber.git
cd transcriber

# Start with Docker Compose
docker-compose up -d

# Access web interface
open http://localhost:5001
```

---

### Windows (Native)

**Best for**: Windows users who prefer native installation

#### Prerequisites

1. **Install Python 3.12**
   - Download from [python.org](https://www.python.org/downloads/)
   - ⚠️ Check "Add Python to PATH" during installation
   - Verify: `python --version`

2. **Install FFmpeg**

   **Option A: Using winget (Recommended)**
   ```powershell
   winget install FFmpeg
   ```

   **Option B: Manual Installation**
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows)
   - Extract to `C:\ffmpeg`
   - Add `C:\ffmpeg\bin` to System PATH:
     1. Open System Properties → Environment Variables
     2. Edit "Path" under System variables
     3. Add new entry: `C:\ffmpeg\bin`
     4. Restart terminal

   Verify: `ffmpeg -version`

3. **Install CUDA (For GPU Support)**
   - Check GPU compatibility: [CUDA GPUs](https://developer.nvidia.com/cuda-gpus)
   - Download CUDA Toolkit: [CUDA Downloads](https://developer.nvidia.com/cuda-downloads)
   - Install latest NVIDIA drivers: [NVIDIA Drivers](https://www.nvidia.com/drivers)
   - Verify: `nvidia-smi`

#### Installation Steps

```powershell
# 1. Clone repository
git clone https://github.com/makoronius/transcriber.git
cd transcriber

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install PyTorch with CUDA support (for GPU)
# For CUDA 11.8:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
# For CUDA 12.1:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
# For CPU only:
pip install torch torchvision torchaudio

# 6. Verify installation
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# 7. Start web application
python web_app.py

# Access at http://localhost:5000
```

---

### Windows (WSL)

**Best for**: Windows users who want Linux environment with GPU support

#### Prerequisites

1. **Install WSL 2**
   ```powershell
   # Open PowerShell as Administrator
   wsl --install
   # Restart computer

   # Verify WSL version
   wsl --list --verbose
   ```

2. **Install Ubuntu in WSL**
   ```powershell
   wsl --install -d Ubuntu-22.04
   ```

3. **Install NVIDIA Driver for WSL** (For GPU)
   - Download: [CUDA on WSL](https://developer.nvidia.com/cuda/wsl)
   - ⚠️ Install Windows driver only, DO NOT install CUDA inside WSL
   - Verify from WSL: `nvidia-smi`

#### Installation Steps

```bash
# 1. Open WSL terminal
wsl

# 2. Update system
sudo apt update && sudo apt upgrade -y

# 3. Install prerequisites
sudo apt install -y python3.12 python3.12-venv python3-pip git ffmpeg

# 4. Clone repository
git clone https://github.com/makoronius/transcriber.git
cd transcriber

# 5. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 6. Install dependencies
pip install -r requirements.txt

# 7. Install PyTorch with CUDA support
# For GPU:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
# For CPU only:
pip install torch torchvision torchaudio

# 8. Verify CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# 9. Start web application
python web_app.py

# Access from Windows browser: http://localhost:5000
```

#### WSL Tips

**Access Windows files**:
```bash
cd /mnt/c/Users/YourUsername/Downloads
```

**Run in background**:
```bash
nohup python web_app.py &
```

**Stop background process**:
```bash
pkill -f web_app.py
```

---

### Ubuntu/Linux

**Best for**: Linux users and servers

#### Prerequisites (Ubuntu 22.04 / 24.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12 (if not available)
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Install other dependencies
sudo apt install -y git ffmpeg python3-pip build-essential
```

#### CUDA Installation (For GPU Support)

**For Ubuntu 22.04**:
```bash
# Install NVIDIA driver
sudo apt install -y nvidia-driver-535

# Add CUDA repository
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update

# Install CUDA Toolkit
sudo apt install -y cuda-toolkit-12-1

# Add to PATH (add to ~/.bashrc)
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Verify
nvidia-smi
nvcc --version
```

**For other distributions**: See [CUDA Linux Installation Guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)

#### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/makoronius/transcriber.git
cd transcriber

# 2. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install PyTorch with CUDA support
# For GPU:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
# For CPU only:
pip install torch torchvision torchaudio

# 5. Verify installation
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'CUDA devices: {torch.cuda.device_count()}')"

# 6. Start web application
python web_app.py

# Access at http://localhost:5000
```

#### Run as System Service (Optional)

```bash
# Create systemd service
sudo nano /etc/systemd/system/whisper-transcriber.service
```

```ini
[Unit]
Description=Whisper AI Transcriber
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/transcriber
Environment="PATH=/path/to/transcriber/venv/bin"
ExecStart=/path/to/transcriber/venv/bin/python web_app.py --port 5000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable whisper-transcriber
sudo systemctl start whisper-transcriber

# Check status
sudo systemctl status whisper-transcriber

# View logs
sudo journalctl -u whisper-transcriber -f
```

---

### macOS

**Best for**: Mac users (Apple Silicon or Intel)

#### Prerequisites

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.12 ffmpeg git

# Verify installations
python3.12 --version
ffmpeg -version
```

#### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/makoronius/transcriber.git
cd transcriber

# 2. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install PyTorch
# For Apple Silicon (M1/M2/M3):
pip install torch torchvision torchaudio

# For Intel Mac (CPU only):
pip install torch torchvision torchaudio

# 5. Verify installation
python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"

# 6. Start web application
python web_app.py

# Access at http://localhost:5000
```

**Note**: Apple Silicon Macs can use MPS (Metal Performance Shaders) for GPU acceleration, but CUDA is not available. Performance is between CPU and NVIDIA GPU.

---

## Post-Installation

### Verify Installation

```bash
# Check Python and packages
python --version
pip list | grep -E "torch|faster-whisper|flask"

# Check FFmpeg
ffmpeg -version

# Check CUDA (if applicable)
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"

# Test transcription
python faster_whisper_latin.py --help
```

### Configure Application

1. **Edit Configuration** (Optional):
   ```bash
   nano config.yaml
   ```

   Adjust settings:
   - Model size (tiny, small, medium, large-v2, large-v3)
   - Device (cuda, cpu)
   - Language preferences
   - Hallucination filters

2. **Add YouTube Cookies** (For Private Videos):
   - Install browser extension: [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Export cookies from YouTube
   - Save as `youtube_cookies.txt` in project root

3. **Create `.env` File**:
   ```bash
   cp .env.example .env
   nano .env
   ```

   Set your preferences:
   ```
   SECRET_KEY=your-generated-secret-key-here
   FLASK_ENV=production
   ```

### First Run

```bash
# Start web application
python web_app.py

# Or with custom port
python web_app.py --port 8080

# Access web interface
open http://localhost:5000
```

The first run will:
- Download Whisper models (~3 GB for large-v3)
- Create necessary directories
- Initialize database

---

## Troubleshooting

### Python Version Issues

**Problem**: Python 3.13 installed but no CUDA support
```bash
# Solution: Install Python 3.12
# Ubuntu:
sudo apt install python3.12 python3.12-venv
# macOS:
brew install python@3.12
# Windows: Download from python.org
```

### CUDA Not Detected

**Problem**: `torch.cuda.is_available()` returns `False`

**Solutions**:
```bash
# 1. Check NVIDIA driver
nvidia-smi

# 2. Verify CUDA installation
nvcc --version

# 3. Reinstall PyTorch with correct CUDA version
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 4. Check PyTorch CUDA version
python -c "import torch; print(torch.version.cuda)"
```

### FFmpeg Not Found

**Problem**: `ffmpeg: command not found`

**Solutions**:
```bash
# Ubuntu/Linux:
sudo apt install ffmpeg

# macOS:
brew install ffmpeg

# Windows: Add to PATH or use winget
winget install FFmpeg
```

### Out of Memory Errors

**Problem**: `CUDA out of memory`

**Solutions**:
1. Use smaller model in `config.yaml`:
   ```yaml
   model: medium  # or small
   ```

2. Reduce workers:
   ```yaml
   workers: 1
   ```

3. Process videos one at a time

4. Close other GPU-intensive applications

### Import Errors

**Problem**: `ModuleNotFoundError`

**Solutions**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.8-3.12
```

### Permission Errors (Linux/Mac)

**Problem**: Permission denied on directories

**Solutions**:
```bash
# Fix ownership
sudo chown -R $USER:$USER yt_downloads uploads logs

# Or run with appropriate permissions
chmod -R 755 yt_downloads uploads logs
```

### WSL-Specific Issues

**Problem**: GPU not accessible in WSL

**Solutions**:
```bash
# 1. Verify WSL 2
wsl --list --verbose  # Should show version 2

# 2. Install WSL NVIDIA driver (from Windows)
# Download from: https://developer.nvidia.com/cuda/wsl

# 3. Check from WSL
nvidia-smi

# 4. DO NOT install CUDA inside WSL (use Windows driver only)
```

### Port Already in Use

**Problem**: `Address already in use: 5000`

**Solutions**:
```bash
# Use different port
python web_app.py --port 8080

# Or find and kill process using port 5000
# Linux/Mac:
lsof -ti:5000 | xargs kill -9
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

---

## Next Steps

After successful installation:

1. **Read Usage Guide**: [USAGE.md](USAGE.md)
2. **Explore Web Interface**: [WEB_INTERFACE.md](WEB_INTERFACE.md)
3. **Docker Setup** (if preferred): [DOCKER_SETUP.md](DOCKER_SETUP.md)
4. **Join Development**: [Contributing Guide](../README.md#contributing)

---

## Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/makoronius/transcriber/issues)
- **Email**: mark.emelianov@gmail.com
- **Documentation**: Check other guides in `/docs` folder

---

**Installation complete! Start transcribing with `python web_app.py`** 🚀
