# Quick Start Guide

## 🚀 Getting Started (3 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Web Interface
```bash
python web_app.py
```

### 3. Open Browser
```
http://localhost:5000
```

**That's it!** You can now transcribe videos through the web interface.

---

## 📌 Common Commands

### Web Interface
```bash
# Start server
python web_app.py

# With custom port
python web_app.py --port 8080
```

### YouTube Transcription
```bash
# Playlist
python transcribe_playlist.py "https://youtube.com/playlist?list=XXXXX"

# Single video
python transcribe_playlist.py "https://youtu.be/VIDEO_ID"

# With options
python transcribe_playlist.py "URL" --workers 2 --model medium
```

### File Transcription
```bash
# Basic
python faster_whisper_latin.py video.mp4

# With options
python faster_whisper_latin.py video.mp4 --model large-v3 --beam 15 --vad True
```

### Subtitle Cleanup
```bash
# Single file
python srt_cleanup.py video.srt

# Batch process
python srt_cleanup.py ./yt_downloads --batch

# Preview changes
python srt_cleanup.py video.srt --dry-run
```

### Docker
```bash
# Web interface (recommended)
docker-compose up web

# CLI - CPU
./docker-run.sh cpu "YOUTUBE_URL"

# CLI - GPU
./docker-run.sh gpu "YOUTUBE_URL" --workers 2
```

---

## 🎛️ Key Parameters

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `--model` | tiny, small, medium, large-v3 | Quality vs speed |
| `--device` | cuda, cpu | GPU or CPU |
| `--language` | sr, en, auto | Target language |
| `--beam` | 5-20 | Accuracy (higher = better) |
| `--workers` | 1-4 | Parallel jobs |
| `--vad` | True, False | Voice detection |

---

## 📂 File Locations

- **Downloads**: `yt_downloads/`
- **Logs**: `transcribe.log`
- **Uploads**: `uploads/`
- **Database**: `jobs.db`
- **Config**: `config.yaml`

---

## ⚠️ Troubleshooting

### GPU not detected
```bash
# Check CUDA
nvidia-smi

# Check Python version (must be 3.12)
python --version

# Install PyTorch with CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Unicode errors
**Fixed!** Already resolved in latest version.

### Port 5000 in use
```bash
# Use different port
python web_app.py --port 5001
```

### Garbage in subtitles
```bash
# Clean them up
python srt_cleanup.py video.srt

# Or edit config.yaml to add patterns
```

---

## 🎯 Best Practices

### For Best Quality
- Use `large-v3` model
- Set `--beam 15` or higher
- Enable `--vad True`
- Use GPU if available

### For Speed
- Use `small` or `medium` model
- Set `--beam 5`
- Disable VAD
- Use CPU for short videos

### For Batch Processing
- Use `--workers 2` or higher (GPU required)
- Enable skip options in config
- Clean up after each batch

---

## 📖 Full Documentation

- **README.md** - Complete installation guide
- **WEB_INTERFACE.md** - Web interface details
- **SUMMARY.md** - Project overview
- **config.yaml** - All configurable options

---

## 🆘 Need Help?

1. Check logs: `tail -f transcribe.log`
2. Try dry-run: `--dry-run`
3. Test manually: `python faster_whisper_latin.py video.mp4`
4. Check config: `cat config.yaml`

---

**Happy transcribing! 🎉**
