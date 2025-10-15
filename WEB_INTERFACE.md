# Web Interface Guide

## Overview

The web interface provides an easy-to-use GUI for transcribing YouTube videos and playlists without using the command line.

## Features

### ✅ Job Submission
- **YouTube URLs**: Paste playlist or single video URLs
- **File Upload**: Upload video files directly (any format supported by FFmpeg)
- **Audio Track Selection**: Choose specific audio track for multi-audio files
- **Cookie Upload**: Support for age-restricted/private videos

### ✅ Configurable Parameters
All parameters are available via dropdown menus:
- **Model**: tiny, small, medium, large-v2, large-v3
- **Device**: GPU (CUDA) or CPU
- **Language**: Serbian, English, Russian, Spanish, French, German, Auto-detect
- **Beam Size**: 5 (fast) to 20 (best quality)
- **Workers**: 1-4 parallel transcription jobs
- **VAD Filter**: Voice Activity Detection (improves quality)

### ✅ Real-Time Monitoring
- Live job status updates (queued → running → completed/failed)
- Progress bar showing transcription progress
- Jobs continue running even if you close the browser
- Reconnects automatically via WebSocket

### ✅ Job Management
- **Active Jobs**: View currently running transcriptions
- **Job History**: Filter by All/Completed/Failed
- **Job Details**: Click any job to see full parameters and logs
- **Persistent Storage**: Jobs are saved to SQLite database

### ✅ File Browser
- View all downloaded videos and subtitles
- Search by filename
- Filter by file type (.mp4, .srt)
- Download files directly from browser
- Auto-refresh when jobs complete

## Installation

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start web server
python web_app.py

# Open browser to http://localhost:5000
```

### With Docker

```bash
# Build and start
docker-compose up web

# Access at http://localhost:5000
```

### Production Deployment

For production, use a proper WSGI server:

```bash
# Install gunicorn
pip install gunicorn

# Run with workers
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 web_app:app
```

## Usage

### Transcribing YouTube Videos

1. Open http://localhost:5000 in your browser
2. Paste YouTube URL (playlist or single video)
3. Configure parameters (or use defaults)
4. Optionally upload cookie file for private videos
5. Click "🚀 Start Transcription"
6. Monitor progress in "Active Jobs" section
7. Download results from "Downloaded Files" section

### Uploading Video Files

1. Switch to "Upload File" tab (coming soon)
2. Click "Browse" to select video file
3. If file has multiple audio tracks, select desired track
4. Configure transcription parameters
5. Click "Start Transcription"
6. File will be transcribed using faster-whisper

### Cleaning Up Subtitles

After transcription, you may want to clean up hallucinated text:

```bash
# Clean single file
python srt_cleanup.py yt_downloads/playlist/video.srt

# Clean all files in directory
python srt_cleanup.py yt_downloads --batch

# Preview changes without saving
python srt_cleanup.py video.srt --dry-run
```

## API Endpoints

The web interface exposes a REST API:

### GET `/api/config`
Get available configuration options (models, devices, languages, etc.)

### POST `/api/submit`
Submit a new transcription job

**Form Data:**
- `url`: YouTube URL or `file://` path
- `source_type`: "youtube" or "upload"
- `model`: Model name
- `device`: "cuda" or "cpu"
- `language`: Language code or "auto"
- `beam_size`: Integer (5-20)
- `workers`: Integer (1-4)
- `vad_filter`: "true" or "false"
- `cookie_file`: File upload (optional)
- `video_file`: File upload (for uploads)

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

### GET `/api/jobs`
Get all jobs

**Response:**
```json
[
  {
    "id": "uuid",
    "url": "https://...",
    "status": "completed",
    "progress": 100,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:45:00",
    "parameters": "{...}",
    "result": "Output log...",
    "error": null
  }
]
```

### GET `/api/jobs/<job_id>`
Get specific job details

### GET `/api/files`
List all downloaded files

**Response:**
```json
[
  {
    "name": "video.mp4",
    "path": "playlist/video.mp4",
    "size": 104857600,
    "modified": "2025-01-15T10:45:00",
    "type": ".mp4"
  }
]
```

### GET `/api/files/<path>`
Download a file

### POST `/api/detect-audio-tracks`
Detect audio tracks in uploaded file

**Form Data:**
- `file`: Video file upload

**Response:**
```json
{
  "tracks": [
    {
      "index": 0,
      "codec": "aac",
      "channels": 2,
      "sample_rate": 48000,
      "language": "eng",
      "title": "English",
      "label": "Track 1: English (2ch)"
    }
  ],
  "filename": "video.mp4"
}
```

## WebSocket Events

The interface uses Socket.IO for real-time updates:

### `connect`
Client connected to server

### `disconnect`
Client disconnected

### `job_update`
Job status changed

**Data:**
```json
{
  "job_id": "uuid",
  "status": "running",
  "progress": 45,
  "result": "Partial output...",
  "error": null
}
```

## Configuration

### Custom Hallucination Filters

Edit `config.yaml` to customize subtitle cleanup:

```yaml
hallucination_filters:
  bad_phrases:
    - "subscribe"
    - "thanks for watching"
    - "Privećajuće"  # Add your patterns here

  bad_patterns:
    - "mmm"
    - "uhh"
    - "je, je, je"

  min_segment_duration: 0.3
  max_repetition_ratio: 0.7
```

These filters apply both during transcription and when using `srt_cleanup.py`.

### Logging

Logs are saved to `transcribe.log` (configurable in `config.yaml`):

```yaml
logging:
  enabled: true
  log_file: "transcribe.log"
  log_level: "INFO"
  max_size_mb: 10
  backup_count: 3
```

## Troubleshooting

### Port 5000 already in use

```bash
# Use different port
python web_app.py --port 5001
```

Or edit `web_app.py`:
```python
socketio.run(app, host='0.0.0.0', port=5001, debug=True)
```

### Jobs not starting

1. Check logs: `tail -f transcribe.log`
2. Verify dependencies: `pip install -r requirements.txt`
3. Test scripts manually: `python faster_whisper_latin.py video.mp4`

### Socket.IO not connecting

1. Clear browser cache
2. Check firewall settings
3. Verify no proxy blocking WebSocket connections

### GPU not detected

1. Verify CUDA: `nvidia-smi`
2. Check PyTorch: `python -c "import torch; print(torch.cuda.is_available())"`
3. Use CPU mode as fallback (slower but works)

## Security Notes

### Production Deployment

⚠️ **Important**: The web interface is designed for local/internal use. For production:

1. **Authentication**: Add login system (Flask-Login)
2. **HTTPS**: Use SSL certificate
3. **Rate Limiting**: Prevent abuse (Flask-Limiter)
4. **File Size Limits**: Already configured (16MB default)
5. **Secret Key**: Change `SECRET_KEY` in production:
   ```python
   app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secure-random-key')
   ```

### File Upload Security

- Filenames are sanitized using `secure_filename()`
- File types are validated by FFmpeg
- Uploads are stored in dedicated directory
- Temporary files are cleaned up after processing

## Advanced Usage

### Custom Transcriber

You can modify the transcription logic by editing `web_app.py`:

```python
def run_transcription_job(job_id, url, parameters):
    # Your custom logic here
    # Call your own transcription script
    cmd = ['python', 'my_custom_script.py', ...]
```

### Database Schema

Jobs are stored in SQLite (`jobs.db`):

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    status TEXT NOT NULL,  -- queued, running, completed, failed, cancelled
    progress INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    parameters TEXT,  -- JSON
    result TEXT,  -- Output logs
    error TEXT  -- Error message
);
```

### Custom UI

All UI files are in `templates/` and `static/`:
- `templates/index.html` - Main HTML structure
- `static/style.css` - Styling
- `static/app.js` - JavaScript logic

Feel free to customize to your needs!

## Next Features

Planned enhancements:
- [ ] Video player with subtitle preview
- [ ] Subtitle editor (inline editing)
- [ ] Bulk operations (batch delete, batch cleanup)
- [ ] Download queue management
- [ ] Statistics dashboard
- [ ] User accounts and authentication
- [ ] API key authentication
- [ ] Webhook notifications

## Contributing

Found a bug or want to add a feature? Contributions welcome!

1. Test the feature locally
2. Document changes
3. Submit pull request

## License

Same as main project.
