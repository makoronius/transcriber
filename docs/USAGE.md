# Usage Guide

Complete guide for using Whisper AI Transcriber for all common tasks.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Web Interface](#web-interface)
- [Command Line Interface](#command-line-interface)
- [Configuration](#configuration)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Using Web Interface (Recommended)

```bash
# Start web server
python web_app.py

# Access in browser
http://localhost:5000
```

That's it! The web interface provides:
- YouTube URL submission
- File uploads
- Real-time progress tracking
- File browser with video player
- System monitoring

See [Web Interface Guide](WEB_INTERFACE.md) for detailed instructions.

### Using Docker

```bash
# Start web interface with Docker
docker-compose up -d

# Access at http://localhost:5001
```

See [Docker Setup](DOCKER_SETUP.md) for more details.

---

## Web Interface

### Starting the Server

**Basic**:
```bash
python web_app.py
```

**Custom Port**:
```bash
python web_app.py --port 8080
```

**Production Mode** (with Gunicorn):
```bash
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 300 web_app:app
```

### Main Features

#### 1. YouTube Transcription
- Paste playlist or video URL
- Configure model, language, workers
- Upload cookies for private videos
- Monitor progress in real-time

#### 2. File Upload
- Upload video/audio files
- Select audio track (for multi-audio files)
- Choose transcription parameters
- Download results

#### 3. File Browser
- View all downloaded files
- Search and filter by type
- Play videos with subtitles
- Download or delete files
- Generate subtitles for existing videos

#### 4. System Monitor
- View CPU, Memory, Disk usage
- Monitor GPU utilization
- Check database health
- Auto-refresh every 15 seconds

---

## Command Line Interface

### YouTube Transcription

**Basic Playlist**:
```bash
python transcribe_playlist.py "https://youtube.com/playlist?list=PLxxxx"
```

**Single Video**:
```bash
python transcribe_playlist.py "https://youtu.be/VIDEO_ID"
```

**With Options**:
```bash
python transcribe_playlist.py "URL" \
  --workers 2 \
  --model large-v3 \
  --download-dir my_videos
```

**Using Cookies**:
```bash
python transcribe_playlist.py "URL" --cookies my_cookies.txt
```

### Direct File Transcription

**Basic**:
```bash
python faster_whisper_latin.py video.mp4
```

**High Quality**:
```bash
python faster_whisper_latin.py video.mp4 \
  --model large-v3 \
  --beam 15 \
  --vad True
```

**Fast Mode**:
```bash
python faster_whisper_latin.py video.mp4 \
  --model small \
  --beam 5 \
  --device cpu
```

**Batch Processing**:
```bash
# Process all MP4 files in directory
for file in *.mp4; do
  python faster_whisper_latin.py "$file"
done
```

### Subtitle Cleanup

**Single File**:
```bash
python srt_cleanup.py video.srt
```

**Preview Changes** (dry-run):
```bash
python srt_cleanup.py video.srt --dry-run
```

**Batch Process Directory**:
```bash
python srt_cleanup.py ./yt_downloads --batch
```

**Backup Before Cleaning**:
```bash
python srt_cleanup.py video.srt --backup
```

### Docker Commands

**Web Interface**:
```bash
# Start
docker-compose up -d

# Stop
docker-compose stop

# View logs
docker-compose logs -f

# Restart
docker-compose restart
```

**CLI Transcription**:
```bash
# Using helper script (CPU)
./docker-run.sh cpu "YOUTUBE_URL"

# Using helper script (GPU)
./docker-run.sh gpu "YOUTUBE_URL" --workers 2

# Direct docker-compose (CPU)
docker-compose run --rm whisper-cpu python transcribe_playlist.py "URL"

# Direct docker-compose (GPU)
docker-compose run --rm whisper-gpu python transcribe_playlist.py "URL"
```

---

## Configuration

### config.yaml Overview

```yaml
download:
  download_dir: yt_downloads
  cookies: youtube_cookies.txt
  workers: 1

transcription:
  model: large-v2
  device: cuda
  language: sr
  beam_size: 10
  vad_filter: true

hallucination_filters:
  bad_phrases:
    - "subscribe"
    - "thanks for watching"
  bad_patterns:
    - "m{3,}"  # Remove "mmm"
```

### Common Settings

#### Model Selection
```yaml
model: large-v3    # Best quality, slower, 8GB VRAM
model: large-v2    # Good quality, 8GB VRAM
model: medium      # Balanced, 4GB VRAM
model: small       # Fast, 2GB VRAM
model: tiny        # Very fast, 1GB VRAM
```

#### Device Selection
```yaml
device: cuda       # GPU (10-50x faster)
device: cpu        # CPU (slower but universal)
```

#### Language Codes
```yaml
language: sr       # Serbian
language: en       # English
language: ru       # Russian
language: es       # Spanish
language: fr       # French
language: de       # German
# See full list: https://github.com/openai/whisper#available-models-and-languages
```

### Cookie Setup

For age-restricted or private videos:

1. **Install Browser Extension**:
   - Chrome: [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. **Export Cookies**:
   - Log in to YouTube
   - Click extension icon
   - Export as `youtube_cookies.txt`

3. **Place in Project Root**:
   ```
   transcriber/
   ├── youtube_cookies.txt  ← Here
   ├── web_app.py
   └── config.yaml
   ```

---

## Advanced Usage

### Parallel Processing

**For Playlists** (requires powerful GPU):
```bash
python transcribe_playlist.py "URL" --workers 3
```

This will:
- Download videos sequentially
- Transcribe up to 3 videos simultaneously
- Requires ~8GB VRAM per worker

### Custom Audio Preprocessing

Edit `faster_whisper_latin.py` to add custom FFmpeg filters:

```python
# Example: Add custom audio filters
ffmpeg_filters = [
    "highpass=f=200",          # Remove low frequency noise
    "lowpass=f=3000",          # Remove high frequency noise
    "afftdn=nf=-25",           # Denoise
    "loudnorm=I=-16:TP=-1.5"   # Normalize loudness
]
```

### Custom Hallucination Filters

Add patterns to `config.yaml`:

```yaml
hallucination_filters:
  bad_phrases:
    - "your custom phrase"
    - "repeated text"

  bad_patterns:
    - "word{3,}"              # Remove repeated word (3+ times)
    - "\\b(\\w+)\\s+\\1\\s+\\1"  # Remove triple repetition
```

### Batch Translation

```bash
# Transcribe first
python transcribe_playlist.py "URL"

# Then translate all SRT files
for file in yt_downloads/**/*.srt; do
  # Use web interface translation feature
  # Or external translation tool
done
```

### API Integration

**Start Web Server**:
```python
from web_app import app
app.run(host='0.0.0.0', port=5000)
```

**Submit Job via API**:
```python
import requests

response = requests.post('http://localhost:5000/api/submit', json={
    'url': 'https://youtu.be/VIDEO_ID',
    'model': 'large-v3',
    'language': 'sr',
    'workers': 1
})

job_id = response.json()['job_id']
```

**Check Job Status**:
```python
status = requests.get(f'http://localhost:5000/api/jobs/{job_id}').json()
print(status['status'])  # queued, running, completed, failed
```

---

## Best Practices

### For Best Quality

**Configuration**:
```yaml
model: large-v3
beam_size: 15
vad_filter: true
temperature: 0.2
```

**Command**:
```bash
python faster_whisper_latin.py video.mp4 \
  --model large-v3 \
  --beam 15 \
  --vad True \
  --temp 0.2
```

**Results**:
- Highest accuracy
- Slower processing (~20-60 min per hour of video)
- Requires 8GB VRAM

### For Speed

**Configuration**:
```yaml
model: small
beam_size: 5
vad_filter: false
```

**Command**:
```bash
python faster_whisper_latin.py video.mp4 \
  --model small \
  --beam 5
```

**Results**:
- Fast processing (~5-10 min per hour of video)
- Good quality for clear audio
- Requires 2GB VRAM

### For Batch Processing

**Script Example**:
```bash
#!/bin/bash
# batch_transcribe.sh

PLAYLIST_FILE="playlists.txt"

while IFS= read -r url; do
  echo "Processing: $url"
  python transcribe_playlist.py "$url" --workers 2

  # Clean up subtitles
  python srt_cleanup.py ./yt_downloads --batch

  # Wait between playlists
  sleep 10
done < "$PLAYLIST_FILE"
```

**Playlists file**:
```
https://youtube.com/playlist?list=PLAYLIST_ID_1
https://youtube.com/playlist?list=PLAYLIST_ID_2
https://youtube.com/playlist?list=PLAYLIST_ID_3
```

### Memory Management

**GPU Memory Issues**:
1. Use smaller model
2. Reduce workers: `--workers 1`
3. Process sequentially
4. Close other GPU applications

**Disk Space**:
1. Clean up after processing:
   ```bash
   # Remove video files, keep subtitles
   find yt_downloads -name "*.mp4" -delete
   ```

2. Enable auto-cleanup in config:
   ```yaml
   download:
     skip_existing_video: true
     skip_existing_srt: true
   ```

---

## Troubleshooting

### Common Issues

#### GPU Not Detected

**Check CUDA**:
```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

**Solution**:
```bash
# Reinstall PyTorch with CUDA
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### Port Already in Use

**Error**: `Address already in use: 5000`

**Solution**:
```bash
# Use different port
python web_app.py --port 8080

# Or kill process on port 5000
lsof -ti:5000 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :5000   # Windows
```

#### Unicode/Encoding Errors

**Already Fixed** in current version! If you see this:
- Update to latest version
- Check Python version: `python --version` (should be 3.8+)

#### Garbage in Subtitles

**Clean them**:
```bash
python srt_cleanup.py video.srt
```

**Adjust filters** in `config.yaml`:
```yaml
hallucination_filters:
  bad_phrases:
    - "your problematic phrase"
```

#### Download Fails (403/429)

**Cause**: Rate limiting or authentication required

**Solutions**:
1. Add YouTube cookies: `--cookies youtube_cookies.txt`
2. Wait between requests
3. Check if video is available in your region

#### Slow Transcription

**If using CPU**:
- Use smaller model: `--model small`
- Reduce beam size: `--beam 5`
- Consider GPU hardware

**If using GPU**:
- Check GPU utilization: `nvidia-smi`
- Verify CUDA is enabled
- Use appropriate model for VRAM

---

## File Locations

Default locations for generated files:

```
transcriber/
├── yt_downloads/           # Downloaded videos and subtitles
│   ├── PlaylistName/
│   │   ├── video.mp4
│   │   └── video.srt
│   └── downloaded.txt      # Download archive
├── uploads/                # Uploaded files
├── logs/                   # Application logs
│   ├── transcribe.log
│   └── web_server.log
├── backups/                # Backup files
├── whisper_jobs.db         # Job database
└── config.yaml             # Configuration
```

---

## Parameter Reference

### transcribe_playlist.py

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | required | YouTube URL (playlist or video) |
| `--download-dir` | string | `yt_downloads` | Output directory |
| `--workers` | int | `1` | Parallel transcription workers |
| `--cookies` | string | `youtube_cookies.txt` | Cookie file path |
| `--skip-existing-video` | flag | enabled | Skip downloaded videos |
| `--skip-existing-srt` | flag | enabled | Skip existing subtitles |

### faster_whisper_latin.py

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | string | required | Video/audio file path |
| `--model` | string | `large-v3` | Whisper model size |
| `--device` | string | `cuda` | Device (cuda/cpu) |
| `--compute` | string | `float16` | Precision mode |
| `--language` | string | `sr` | Target language code |
| `--beam` | int | `12` | Beam search size |
| `--vad` | bool | `False` | Enable VAD filter |
| `--temp` | float | `0.2` | Sampling temperature |

### srt_cleanup.py

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | string | required | SRT file or directory path |
| `--batch` | flag | disabled | Process entire directory |
| `--dry-run` | flag | disabled | Preview without saving |
| `--backup` | flag | disabled | Create backup before cleaning |

---

## Next Steps

- **Web Interface**: See [WEB_INTERFACE.md](WEB_INTERFACE.md)
- **Docker Setup**: See [DOCKER_SETUP.md](DOCKER_SETUP.md)
- **Installation**: See [INSTALLATION.md](INSTALLATION.md)
- **Main README**: See [../README.md](../README.md)

---

**Need help?** Contact mark.emelianov@gmail.com or [open an issue](https://github.com/makoronius/transcriber/issues)
