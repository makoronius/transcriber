# YouTube Playlist Transcriber

Automatically download YouTube playlists and transcribe them to SRT subtitles using faster-whisper on GPU. Optimized for Serbian content with Cyrillic-to-Latin transliteration and advanced hallucination filtering.

## Quick Start

**🌐 Web Interface** (NEW!): Modern GUI for easy transcription ([Web Interface](#web-interface-new))

**🐳 Docker**: Easiest setup with all dependencies ([Docker Installation](#docker-installation-recommended))

**💻 Command Line**: Traditional installation with Python ([Installation](#installation))

## Features

- **Parallel Processing**: Downloads and transcribes videos concurrently with configurable workers
- **Smart Resume**: Automatically detects already-downloaded videos and missing subtitles
- **GPU Acceleration**: Uses faster-whisper with CUDA for high-speed transcription
- **Audio Enhancement**: FFmpeg preprocessing with RNNoise denoising and loudness normalization
- **Cyrillic Transliteration**: Automatically converts Serbian Cyrillic text to Latin alphabet
- **Hallucination Filter**: Removes repeated filler words, subscription prompts, and other garbage
- **Cookie Support**: Download age-restricted and private videos using browser cookies
- **Live Queue**: Videos are transcribed immediately as downloads complete
- **Timestamped Logging**: Full visibility into download and transcription progress
- **Web Interface**: Modern GUI with real-time monitoring (NEW!)
- **SRT Cleanup**: Advanced subtitle cleanup tool with configurable filters (NEW!)

## Web Interface (NEW!)

We now provide a modern web interface for easy transcription without using the command line!

### Features
- ✅ **YouTube & File Upload**: Submit URLs or upload video files
- ✅ **Real-Time Monitoring**: Live progress updates via WebSocket
- ✅ **Background Jobs**: Jobs continue even if you close the browser
- ✅ **Configurable Parameters**: All settings via dropdown menus (model, language, beam size, etc.)
- ✅ **File Browser**: Search, filter, and download results
- ✅ **Job History**: Track all transcriptions with filtering
- ✅ **Cookie Upload**: Support for private/age-restricted videos
- ✅ **Audio Track Selection**: Choose specific audio track for multi-audio files

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start web server
python web_app.py

# Open browser
http://localhost:5000
```

### With Docker

```bash
# Start web interface
docker-compose up web

# Access at http://localhost:5000
```

### Screenshots & Documentation

See [WEB_INTERFACE.md](WEB_INTERFACE.md) for detailed documentation, API reference, and advanced usage.

### SRT Cleanup Tool

Clean up hallucinated text from subtitle files:

```bash
# Clean single file
python srt_cleanup.py video.srt

# Batch process directory
python srt_cleanup.py yt_downloads --batch

# Preview changes without saving
python srt_cleanup.py video.srt --dry-run
```

**What it removes:**
- Repeated patterns ("je, je, je, je", "Privećajuće")
- Filler text ("mmm", "uhh", "aaa")
- Subscription prompts ("thanks for watching", "subscribe")
- High repetition segments (configurable threshold)
- Very short or garbage segments

**Customizable via config.yaml** - Add your own patterns!

## Requirements

### System Requirements

#### Python Version
- **Python 3.8 - 3.12** (required)
- **⚠️ IMPORTANT**: For GPU/CUDA support, use **Python 3.12** (not 3.13)
  - As of now, PyTorch with CUDA support is not available for Python 3.13
  - CPU-only mode works with Python 3.13, but is 10-50x slower
  - Download Python 3.12: [python.org/downloads](https://www.python.org/downloads/)
  - Check your version: `python --version`

#### FFmpeg (Required)
FFmpeg is required for audio extraction and preprocessing.

**Installation:**
- **Windows**:
  - Using winget: `winget install FFmpeg`
  - Or download from [ffmpeg.org](https://ffmpeg.org/download.html)
  - Add to PATH after installation
- **Linux**:
  - Debian/Ubuntu: `sudo apt install ffmpeg`
  - RHEL/Fedora: `sudo yum install ffmpeg`
  - Arch: `sudo pacman -S ffmpeg`
- **macOS**:
  - Using Homebrew: `brew install ffmpeg`
  - Or download from [ffmpeg.org](https://ffmpeg.org/download.html)

**Verify installation:**
```bash
ffmpeg -version
```

#### NVIDIA GPU with CUDA (Optional but Recommended)
For GPU acceleration (10-50x faster transcription):
- **NVIDIA GPU** with Compute Capability 3.5 or higher
  - Check compatibility: [developer.nvidia.com/cuda-gpus](https://developer.nvidia.com/cuda-gpus)
- **CUDA Toolkit 11.8 or 12.x**
  - Download: [developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads)
  - Windows users: Install CUDA Toolkit from NVIDIA website
  - Linux users: Follow [CUDA installation guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
- **NVIDIA GPU Driver** (latest recommended)
  - Download: [nvidia.com/drivers](https://www.nvidia.com/drivers)

**Verify CUDA installation:**
```bash
nvidia-smi
nvcc --version
```

#### Disk Space
- **Minimum**: 10 GB free space (for models and temporary files)
- **Recommended**: 50+ GB for downloading and processing playlists
- Models are downloaded on first run (~3 GB for large-v3)

### Python Dependencies

Install using the provided `requirements.txt`:
```bash
pip install -r requirements.txt
```

Or install packages individually:

#### Core Packages (Required)
```bash
pip install yt-dlp>=2023.10.13
pip install faster-whisper>=0.10.0
pip install transliterate>=1.10.2
pip install tqdm>=4.66.0
pip install pyyaml>=6.0.1
```

**Package References:**
- **yt-dlp**: [github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloader
- **faster-whisper**: [github.com/guillaumekln/faster-whisper](https://github.com/guillaumekln/faster-whisper) - Optimized Whisper implementation
- **transliterate**: [pypi.org/project/transliterate](https://pypi.org/project/transliterate) - Cyrillic transliteration

#### GPU Acceleration (Highly Recommended)
For CUDA support with Python 3.12:
```bash
# For CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**PyTorch Reference:**
- Official installation guide: [pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/)
- Select your configuration to get the correct install command

#### CPU-Only Installation
If you don't have an NVIDIA GPU or want CPU-only mode:
```bash
pip install torch torchvision torchaudio
```
**Note**: CPU transcription is much slower (10-50x) than GPU.

## Installation

### Quick Start

1. **Verify Prerequisites**:
   ```bash
   python --version  # Should be 3.8-3.12 (use 3.12 for GPU support)
   ffmpeg -version   # Should display FFmpeg version
   nvidia-smi        # (Optional) Should display GPU info if using CUDA
   ```

2. **Clone or download this repository**:
   ```bash
   git clone <repository-url>
   cd whisper
   ```

3. **Create a virtual environment** (recommended):
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate it
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   # Install all required packages
   pip install -r requirements.txt

   # Install PyTorch with CUDA support (Python 3.12 only)
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

5. **Verify installation**:
   ```bash
   # Test if CUDA is available
   python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

   # Test FFmpeg
   ffmpeg -version
   ```

### Troubleshooting Installation

**Python 3.13 users**: Downgrade to Python 3.12 for GPU support:
```bash
# Using pyenv (recommended)
pyenv install 3.12.0
pyenv local 3.12.0

# Or download Python 3.12 from python.org and reinstall
```

**CUDA not detected**:
- Verify NVIDIA drivers are installed: `nvidia-smi`
- Check CUDA Toolkit is installed: `nvcc --version`
- Reinstall PyTorch with correct CUDA version
- See [PyTorch installation guide](https://pytorch.org/get-started/locally/)

**FFmpeg not found**:
- Ensure FFmpeg is in your system PATH
- Windows: Add FFmpeg bin directory to PATH environment variable
- Linux/Mac: Install via package manager as shown above

## Docker Installation (Recommended)

Docker provides the easiest setup with all dependencies pre-configured, including Python 3.12, FFmpeg, and optional CUDA support.

### Prerequisites for Docker

- **Docker**: [Get Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Usually included with Docker Desktop
- **NVIDIA Docker** (for GPU): [nvidia-docker](https://github.com/NVIDIA/nvidia-docker) (Linux only)

**Verify Docker installation:**
```bash
docker --version
docker-compose --version

# For GPU support (Linux)
nvidia-docker --version
```

### Quick Start with Docker

#### Option 1: Using Helper Scripts (Easiest)

We provide helper scripts for easy Docker usage:

**Linux/Mac:**
```bash
# Make script executable (first time only)
chmod +x docker-run.sh

# Run with CPU
./docker-run.sh cpu "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID"

# Run with GPU
./docker-run.sh gpu "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID" --workers 2

# Interactive mode (no URL)
./docker-run.sh cpu
```

**Windows (PowerShell):**
```powershell
# Run with CPU
.\docker-run.ps1 cpu "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID"

# Run with GPU (requires WSL 2)
.\docker-run.ps1 gpu "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID" -ExtraArgs "--workers", "2"

# Interactive mode
.\docker-run.ps1 cpu
```

#### Option 2: Using Docker Compose (Recommended)

**For CPU-only transcription:**
```bash
# Build the image
docker-compose build whisper-cpu

# Run with your playlist URL
docker-compose run --rm whisper-cpu python transcribe_playlist.py "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID"

# Or start an interactive session
docker-compose run --rm whisper-cpu bash
```

**For GPU-accelerated transcription (Linux with NVIDIA GPU):**
```bash
# Build the GPU image
docker-compose build whisper-gpu

# Run with your playlist URL
docker-compose run --rm whisper-gpu python transcribe_playlist.py "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID" --workers 2

# Or start an interactive session
docker-compose run --rm whisper-gpu bash
```

#### Option 2: Using Docker directly

**CPU version:**
```bash
# Build
docker build -t whisper-transcriber:cpu .

# Run
docker run --rm -v ./yt_downloads:/app/yt_downloads whisper-transcriber:cpu \
    python transcribe_playlist.py "YOUR_PLAYLIST_URL"
```

**GPU version (Linux only):**
```bash
# Build
docker build -f Dockerfile.gpu -t whisper-transcriber:gpu .

# Run with GPU
docker run --rm --gpus all -v ./yt_downloads:/app/yt_downloads whisper-transcriber:gpu \
    python transcribe_playlist.py "YOUR_PLAYLIST_URL" --workers 2
```

### Docker Configuration

#### Using Cookie Files
Place your `youtube_cookies.txt` in the project directory before building. The Docker setup automatically mounts it:
```bash
# Cookie file should be in the same directory as docker-compose.yml
./youtube_cookies.txt
```

#### Customizing Settings
Edit `config.yaml` before building to change default settings. The file is mounted read-only into the container.

#### Persistent Data
Docker volumes are configured for:
- **Downloads**: `./yt_downloads` - All downloaded videos and subtitles
- **Logs**: `./logs` - Transcription logs

### Docker on Windows with GPU

**⚠️ Note**: Docker GPU support on Windows requires:
1. **Windows 11** or **Windows 10 21H2+**
2. **WSL 2** (Windows Subsystem for Linux 2)
3. **NVIDIA GPU driver** for WSL
4. **Docker Desktop for Windows** with WSL 2 backend

**Setup steps:**
```powershell
# 1. Install WSL 2
wsl --install

# 2. Install NVIDIA driver for WSL
# Download from: https://developer.nvidia.com/cuda/wsl

# 3. Verify GPU access in WSL
wsl
nvidia-smi

# 4. Run GPU container from WSL terminal
docker-compose run --rm whisper-gpu python transcribe_playlist.py "YOUR_URL"
```

**Alternative for Windows users**: Use CPU version (still faster than many think) or install natively.

### Docker Advantages

✅ **No dependency conflicts** - Everything is isolated
✅ **Correct Python version** - Always uses Python 3.12
✅ **FFmpeg included** - Pre-installed and configured
✅ **Easy cleanup** - Remove containers without affecting your system
✅ **Reproducible** - Same environment on any machine
✅ **Version management** - Switch between CPU/GPU easily

### Docker Troubleshooting

**Build fails with "no space left on device":**
```bash
# Clean up Docker
docker system prune -a
```

**GPU not detected in container:**
```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# Check nvidia-docker installation
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**Permission denied on volumes:**
```bash
# Linux: Fix permissions
sudo chown -R $USER:$USER yt_downloads logs

# Or run with user ID
docker-compose run --rm --user $(id -u):$(id -g) whisper-cpu python transcribe_playlist.py "URL"
```

**Slow performance with CPU version:**
- Consider using smaller model: Edit `config.yaml` and set `model: medium` or `model: small`
- Reduce workers to 1
- Or use GPU version if available

## Usage

### Basic Usage

```bash
python transcribe_playlist.py "https://youtube.com/playlist?list=PLAYLIST_ID"
```

### With Parallel Workers

Process multiple videos simultaneously (requires powerful GPU):
```bash
python transcribe_playlist.py "PLAYLIST_URL" --workers 3
```

### Single Video Transcription

Transcribe a single video file directly:
```bash
python faster_whisper_latin.py "video.mp4"
```

### Advanced Options

```bash
# Custom output directory
python transcribe_playlist.py "URL" --download-dir "my_videos"

# Use different Whisper model
python faster_whisper_latin.py "video.mp4" --model medium --beam 15

# Enable VAD (Voice Activity Detection) for better accuracy
python faster_whisper_latin.py "video.mp4" --vad True --temp 0.3

# Use custom cookie file
python transcribe_playlist.py "URL" --cookies my_cookies.txt
```

## Configuration

### Cookie Setup (for Age-Restricted/Private Videos)

To download age-restricted or private videos, you need to provide YouTube cookies:

1. **Using Browser Extension**:
   - Install "Get cookies.txt LOCALLY" extension for [Chrome](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) or [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
   - Log in to YouTube
   - Click the extension icon and export cookies
   - Save as `youtube_cookies.txt` in the project directory

2. **File Validation**: The script automatically validates your cookie file and warns if it appears incomplete

### Transcription Parameters

#### faster_whisper_latin.py Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--model` | large-v3 | Whisper model (tiny, small, medium, large-v2, large-v3) |
| `--device` | cuda | Device to use (cuda or cpu) |
| `--compute` | float16 | Precision (float16, float32, int8_float16) |
| `--language` | sr | Language code (sr=Serbian, en=English, etc.) |
| `--beam` | 12 | Beam search size (higher = more accurate, slower) |
| `--vad` | False | Enable Voice Activity Detection |
| `--temp` | 0.2 | Temperature (0.0=deterministic, higher=more diverse) |

#### transcribe_playlist.py Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--download-dir` | yt_downloads | Folder for downloaded videos |
| `--workers` | 1 | Number of parallel transcription workers |
| `--cookies` | youtube_cookies.txt | Cookie file for authentication |
| `--skip-existing-srt` | True | Skip files that already have subtitles |
| `--skip-existing-video` | True | Skip previously downloaded videos |

## How It Works

### Workflow

1. **Pre-scan**: Checks for existing downloads missing subtitles and queues them
2. **Download**: Uses yt-dlp to download playlist videos (best quality MP4)
3. **Queue**: Each completed video is immediately added to the transcription queue
4. **Preprocess**: FFmpeg extracts and cleans audio (RNNoise + loudness normalization)
5. **Transcribe**: faster-whisper generates timestamped text with CUDA acceleration
6. **Transliterate**: Converts Serbian Cyrillic text to Latin alphabet
7. **Filter**: Removes hallucinated content (filler words, repeated patterns)
8. **Output**: Saves clean `.srt` subtitle file alongside video

### Hallucination Detection

The transcriber automatically filters:
- Repeated filler sounds: "mmm", "uhh", "aaa"
- Subscription prompts: "thanks for watching", "subscribe"
- Repeated patterns: "da, da, da", "je je je je"
- Very short segments (<0.3 seconds)
- Single-word/character garbage

## Output Structure

```
yt_downloads/
├── PlaylistName/
│   ├── 1 - Video Title.mp4
│   ├── 1 - Video Title.srt          # Generated subtitles
│   ├── 2 - Another Video.mp4
│   └── 2 - Another Video.srt
└── downloaded.txt                     # Download archive
```

## Troubleshooting

### "CUDA out of memory"
- Reduce `--workers` to 1
- Use smaller model: `--model medium` or `--model small`
- Process videos sequentially instead of parallel

### Downloads fail with 403/429 errors
- Add valid YouTube cookies using `--cookies`
- Wait a few minutes between retries (rate limiting)
- Check if videos are region-restricted

### Poor transcription quality
- Increase beam size: `--beam 15` or `--beam 20`
- Enable VAD: `--vad True`
- Adjust temperature for noisy audio: `--temp 0.3` or `--temp 0.4`
- Use larger model: `--model large-v3` (default)

### FFmpeg preprocessing fails
- Ensure FFmpeg is in PATH: `ffmpeg -version`
- RNNoise model is optional; script falls back to loudnorm only
- Check audio file isn't corrupted

### Subtitles contain garbage text
- Adjust hallucination filters in `faster_whisper_latin.py` (lines 44-71)
- Increase `--no-speech-threshold` (default 0.1)
- Lower `--compression-threshold` (default 2.8)

## Performance

### Model Comparison (RTX 3080, 1-hour video)

| Model | VRAM | Speed | Quality |
|-------|------|-------|---------|
| tiny | ~1 GB | 2 min | Fair |
| small | ~2 GB | 5 min | Good |
| medium | ~4 GB | 10 min | Very Good |
| large-v3 | ~8 GB | 20 min | Excellent |

*CPU-only: 10-50x slower depending on processor*

## Credits

- **faster-whisper**: [guillaumekln/faster-whisper](https://github.com/guillaumekln/faster-whisper)
- **yt-dlp**: [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **OpenAI Whisper**: [openai/whisper](https://github.com/openai/whisper)
- **RNNoise**: Xiph.Org noise suppression library

## License

This project is provided as-is for educational and personal use. Respect YouTube's Terms of Service and copyright laws when downloading content.
