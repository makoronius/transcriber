"""
Web interface for YouTube Playlist Transcriber
Provides a simple UI for submitting transcription jobs and monitoring progress
"""

import os
import json
import sqlite3
import logging
import yaml
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import threading
import re
import uuid
import signal
import psutil

# Global dictionary to track active processes for job cancellation
active_job_processes = {}

# Translation library (with fallback)
try:
    from googletrans import Translator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("Warning: googletrans not installed. Translation features will be disabled.")
    print("Install with: pip install googletrans==4.0.0rc1")

# Import transcription module
try:
    from faster_whisper_latin import transcribe_file
    TRANSCRIPTION_AVAILABLE = True
except ImportError:
    TRANSCRIPTION_AVAILABLE = False
    print("Warning: faster_whisper_latin module not found. Transcription will use subprocess fallback.")

# Import yt-dlp for direct downloads
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    print("Warning: yt-dlp module not found. Downloads will use subprocess fallback.")

# Import transcribe_single module
try:
    from transcribe_single import transcribe_single_video
    TRANSCRIBE_SINGLE_AVAILABLE = True
except ImportError:
    TRANSCRIBE_SINGLE_AVAILABLE = False
    print("Warning: transcribe_single module not found. Will use subprocess fallback.")

# Set up comprehensive logging using basicConfig (more reliable)
os.makedirs('logs', exist_ok=True)

# Read logging configuration
log_config = {}
if os.path.exists('config.yaml'):
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            log_config = config.get('web_server_logging', {})
    except Exception as e:
        print(f"Warning: Could not read logging config: {e}")

# Get configuration values
log_file = log_config.get('log_file', 'logs/web_server.log')
log_level_str = log_config.get('log_level', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)

# Configure root logger
logging.basicConfig(
    level=log_level,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True  # Force reconfiguration
)

# Get our logger
logger = logging.getLogger('whisper_web')
logger.setLevel(log_level)

logger.info("="*80)
logger.info("Whisper Web Server Starting")
logger.info("="*80)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'yt_downloads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB max upload (for large video files)

socketio = SocketIO(app, cors_allowed_origins="*")

# Error handlers to ensure JSON responses for API endpoints
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors with JSON response"""
    max_size_gb = app.config.get('MAX_CONTENT_LENGTH', 0) / (1024 * 1024 * 1024)
    logger.error(f"File upload rejected: exceeds {max_size_gb}GB limit")
    return jsonify({
        'error': f'File too large. Maximum upload size is {max_size_gb:.0f}GB'
    }), 413

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors with JSON response for API requests"""
    # Check if this is an API request
    if request.path.startswith('/api/'):
        logger.error(f"Internal server error on {request.path}: {error}", exc_info=True)
        return jsonify({
            'error': 'Internal server error. Please check server logs.'
        }), 500
    # For non-API requests, use default HTML error page
    return error

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Database setup for job tracking
def init_db():
    conn = sqlite3.connect('jobs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (id TEXT PRIMARY KEY,
                  url TEXT NOT NULL,
                  status TEXT NOT NULL,
                  progress INTEGER DEFAULT 0,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  parameters TEXT,
                  result TEXT,
                  error TEXT,
                  job_type TEXT DEFAULT 'transcribe',
                  parent_job_id TEXT,
                  video_path TEXT)''')

    # Add new columns to existing database if they don't exist
    try:
        c.execute("ALTER TABLE jobs ADD COLUMN job_type TEXT DEFAULT 'transcribe'")
        logger.info("Added job_type column to jobs table")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        c.execute("ALTER TABLE jobs ADD COLUMN parent_job_id TEXT")
        logger.info("Added parent_job_id column to jobs table")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        c.execute("ALTER TABLE jobs ADD COLUMN video_path TEXT")
        logger.info("Added video_path column to jobs table")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()

init_db()


def get_db():
    conn = sqlite3.connect('jobs.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """Main page"""
    app.logger.info("Page loaded: /")
    return render_template('index.html')


@app.route('/api/logger-test')
def logger_test():
    """Test endpoint to verify logger is working"""
    logger.debug("DEBUG test message")
    logger.info("INFO test message")
    logger.warning("WARNING test message")

    # Get root logger handlers since we're using basicConfig
    root_logger = logging.getLogger()

    return jsonify({
        'status': 'ok',
        'logger_name': logger.name,
        'logger_level': logging.getLevelName(logger.level),
        'root_handlers': len(root_logger.handlers),
        'handler_details': [
            {
                'type': type(h).__name__,
                'level': logging.getLevelName(h.level)
            } for h in root_logger.handlers
        ]
    })


@app.route('/api/detect-audio-tracks', methods=['POST'])
def detect_audio_tracks():
    """Detect audio tracks in uploaded file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Save temporarily
    filename = secure_filename(file.filename)
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{filename}')
    file.save(temp_path)

    try:
        # Use ffprobe to detect audio streams
        import subprocess
        import json as json_module

        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=index,codec_name,channels,channel_layout,sample_rate:stream_tags=language,title',
            '-of', 'json',
            temp_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({'error': 'Failed to analyze file'}), 500

        data = json_module.loads(result.stdout)
        streams = data.get('streams', [])

        audio_tracks = []
        for i, stream in enumerate(streams):
            tags = stream.get('tags', {})
            track_info = {
                'index': stream.get('index', i),
                'codec': stream.get('codec_name', 'unknown'),
                'channels': stream.get('channels', 0),
                'sample_rate': stream.get('sample_rate', 0),
                'language': tags.get('language', 'und'),
                'title': tags.get('title', f'Audio Track {i+1}'),
                'label': f"Track {i+1}: {tags.get('title', tags.get('language', 'unknown'))} ({stream.get('channels', 0)}ch)"
            }
            audio_tracks.append(track_info)

        return jsonify({'tracks': audio_tracks, 'filename': filename})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/api/config')
def get_config():
    """Get available configuration options"""
    config = {
        'models': [
            {'value': 'tiny', 'label': 'Tiny (Fastest, ~1GB VRAM)'},
            {'value': 'small', 'label': 'Small (Fast, ~2GB VRAM)'},
            {'value': 'medium', 'label': 'Medium (Balanced, ~4GB VRAM)'},
            {'value': 'large-v2', 'label': 'Large-v2 (Accurate, ~8GB VRAM)'},
            {'value': 'large-v3', 'label': 'Large-v3 (Best, ~8GB VRAM)'}
        ],
        'devices': [
            {'value': 'cuda', 'label': 'GPU (CUDA)'},
            {'value': 'cpu', 'label': 'CPU (Slower)'}
        ],
        'languages': [
            {'value': 'auto', 'label': 'Auto-detect'},
            {'value': 'en', 'label': 'English'},
            {'value': 'sr', 'label': 'Serbian'},
            {'value': 'ru', 'label': 'Russian'},
            {'value': 'es', 'label': 'Spanish'},
            {'value': 'fr', 'label': 'French'},
            {'value': 'de', 'label': 'German'},
            {'value': 'it', 'label': 'Italian'},
            {'value': 'pt', 'label': 'Portuguese'},
            {'value': 'pl', 'label': 'Polish'},
            {'value': 'uk', 'label': 'Ukrainian'},
            {'value': 'tr', 'label': 'Turkish'},
            {'value': 'nl', 'label': 'Dutch'},
            {'value': 'ar', 'label': 'Arabic'},
            {'value': 'zh', 'label': 'Chinese'},
            {'value': 'ja', 'label': 'Japanese'},
            {'value': 'ko', 'label': 'Korean'},
            {'value': 'hi', 'label': 'Hindi'},
            {'value': 'cs', 'label': 'Czech'},
            {'value': 'sk', 'label': 'Slovak'},
            {'value': 'bg', 'label': 'Bulgarian'},
            {'value': 'hr', 'label': 'Croatian'},
            {'value': 'sl', 'label': 'Slovenian'},
            {'value': 'mk', 'label': 'Macedonian'}
        ],
        'beam_sizes': [
            {'value': 1, 'label': '1 (Fastest, greedy)'},
            {'value': 3, 'label': '3 (Very Fast)'},
            {'value': 5, 'label': '5 (Fast)'},
            {'value': 7, 'label': '7 (Good)'},
            {'value': 10, 'label': '10 (Balanced)'},
            {'value': 12, 'label': '12 (Better)'},
            {'value': 15, 'label': '15 (Great)'},
            {'value': 20, 'label': '20 (Excellent)'},
            {'value': 25, 'label': '25 (Best Quality)'}
        ],
        'workers': [
            {'value': 1, 'label': '1 (Sequential)'},
            {'value': 2, 'label': '2 (Parallel)'},
            {'value': 3, 'label': '3 (Parallel)'},
            {'value': 4, 'label': '4 (Parallel)'}
        ],
        'vad_options': [
            {'value': 'false', 'label': 'Disabled'},
            {'value': 'true', 'label': 'Enabled (Better quality)'}
        ],
        'compute_types': [
            {'value': 'float16', 'label': 'Float16 (Fastest, GPU)'},
            {'value': 'float32', 'label': 'Float32 (CPU compatible)'},
            {'value': 'int8_float16', 'label': 'Int8 (Fastest, quantized)'}
        ],
        'temperatures': [
            {'value': 0.0, 'label': '0.0 (Deterministic, no randomness)'},
            {'value': 0.1, 'label': '0.1 (Very low)'},
            {'value': 0.2, 'label': '0.2 (Recommended)'},
            {'value': 0.3, 'label': '0.3 (Slightly creative)'},
            {'value': 0.4, 'label': '0.4 (Noisy speech)'},
            {'value': 0.5, 'label': '0.5 (Moderate)'},
            {'value': 0.6, 'label': '0.6 (Very noisy)'},
            {'value': 0.7, 'label': '0.7 (High noise tolerance)'},
            {'value': 0.8, 'label': '0.8 (Extreme noise)'}
        ]
    }
    return jsonify(config)


@app.route('/api/submit', methods=['POST'])
def submit_job():
    """Submit a new transcription job"""
    # Use root logger and app.logger
    logging.info("="*60)
    logging.info("NEW JOB SUBMISSION RECEIVED")
    app.logger.info("NEW JOB SUBMISSION - via app.logger")

    data = request.form
    url = data.get('url', '').strip()
    source_type = data.get('source_type', 'youtube')  # 'youtube', 'upload', or 'existing'

    logging.info(f"Source type: {source_type}")
    logging.info(f"URL: {url}")
    app.logger.info(f"URL via app.logger: {url}")

    if source_type == 'youtube':
        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Validate URL
        if 'youtube.com' not in url and 'youtu.be' not in url:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
    elif source_type == 'upload':
        # Check if using temporary file (after stream selection)
        temp_file_path = data.get('temp_file_path', '')

        if temp_file_path and os.path.exists(temp_file_path):
            # Move temp file to final location
            filename = os.path.basename(temp_file_path).replace('temp_', '')
            final_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)

            # Add timestamp if file exists
            if os.path.exists(final_path):
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{name}_{timestamp}{ext}"
                final_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)

            # Move file
            import shutil
            shutil.move(temp_file_path, final_path)
            upload_path = final_path
        else:
            # Handle direct file upload (legacy path)
            if 'video_file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400

            file = request.files['video_file']
            if not file or not file.filename:
                return jsonify({'error': 'No file selected'}), 400

            # Save uploaded file
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)

        url = f'file://{upload_path}'  # Use file:// protocol for local files
    elif source_type == 'existing':
        # Handle existing file selection
        existing_file_path = data.get('existing_file_path', data.get('existing_file', ''))

        if not existing_file_path:
            return jsonify({'error': 'No file selected'}), 400

        # Construct full path
        full_path = os.path.join(app.config['DOWNLOAD_FOLDER'], existing_file_path)

        if not os.path.exists(full_path):
            return jsonify({'error': 'File not found'}), 404

        url = f'file://{full_path}'  # Use file:// protocol for local files
    else:
        return jsonify({'error': 'Invalid source type'}), 400

    # Handle cookie file upload - save permanently to youtube_cookies.txt
    cookie_file = None
    if 'cookie_file' in request.files:
        file = request.files['cookie_file']
        if file and file.filename:
            # Save to permanent location
            cookie_path = 'youtube_cookies.txt'
            file.save(cookie_path)
            cookie_file = cookie_path

    # If no cookie uploaded, check if youtube_cookies.txt exists
    if not cookie_file and os.path.exists('youtube_cookies.txt'):
        cookie_file = 'youtube_cookies.txt'

    # Parse parameters
    parameters = {
        'model': data.get('model', 'large-v3'),
        'device': data.get('device', 'cuda'),
        'language': data.get('language', 'sr'),
        'beam_size': int(data.get('beam_size', 12)),
        'workers': int(data.get('workers', 1)),
        'vad_filter': data.get('vad_filter', 'false').lower() == 'true',
        'compute_type': data.get('compute_type', 'float16'),
        'temperature': float(data.get('temperature', 0.2)),
        'cookie_file': cookie_file,
        'audio_track': data.get('audio_track', '0'),  # Audio track index
        'source_type': source_type,
        'auto_cleanup': data.get('auto_cleanup', 'false').lower() == 'true'
    }

    # Create job ID
    import uuid
    job_id = str(uuid.uuid4())

    # Extract video title
    video_title = "Unknown Video"
    app.logger.info(f"Extracting video title for source_type: {source_type}, URL: {url}")

    try:
        if source_type == 'youtube':
            # Try to extract title from YouTube using yt-dlp
            from yt_dlp import YoutubeDL
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': 'in_playlist'  # Don't download playlist entries
            }
            if parameters.get('cookie_file') and os.path.exists(parameters['cookie_file']):
                ydl_opts['cookiefile'] = parameters['cookie_file']

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                    # Check if this is a playlist
                    if info.get('_type') == 'playlist':
                        # It's a playlist, get playlist title
                        video_title = info.get('title', info.get('playlist_title', 'YouTube Playlist'))
                        video_count = len(info.get('entries', []))
                        video_title = f"{video_title} ({video_count} videos)"
                        app.logger.info(f"Extracted playlist title: {video_title}")
                    else:
                        # It's a single video
                        video_title = info.get('title', 'Unknown')
                        # Add channel name if available
                        channel = info.get('uploader', info.get('channel', ''))
                        if channel:
                            video_title = f"{video_title} - {channel}"
                        app.logger.info(f"Extracted video title: {video_title}")
            except Exception as e:
                app.logger.warning(f"Could not extract YouTube title: {e}")
                # Try to get some info from URL
                if 'playlist?' in url or ('list=' in url and 'watch' in url):
                    video_title = "YouTube Playlist"
                else:
                    video_title = "YouTube Video"
        elif source_type in ('upload', 'existing'):
            # Extract filename without extension and clean it up
            file_path = url.replace('file://', '')
            # Normalize path separators
            file_path = file_path.replace('\\', '/').replace('//', '/')
            video_title = os.path.splitext(os.path.basename(file_path))[0]
            # Remove common patterns like [VIDEO_ID] from filename
            import re
            video_title = re.sub(r'\s*\[[a-zA-Z0-9_-]{11}\]$', '', video_title)  # Remove YouTube ID
            video_title = re.sub(r'\s*\(\d+\)$', '', video_title)  # Remove (1) numbering
            video_title = video_title.strip()
            if video_title:  # Only update if we got a valid title
                app.logger.info(f"Extracted local file title: {video_title}")
            else:
                video_title = "Local Video"
                app.logger.warning(f"Could not extract title from path: {file_path}")
    except Exception as e:
        app.logger.error(f"Error extracting video title: {e}", exc_info=True)

    parameters['video_title'] = video_title

    app.logger.info(f"Created job ID: {job_id}")
    app.logger.debug(f"Parameters: {json.dumps(parameters, indent=2)}")

    # Determine job type based on source
    # For YouTube URLs: Create download job first
    # For local files: Create transcribe job directly
    if source_type == 'youtube':
        job_type = 'download'
        app.logger.info(f"Creating DOWNLOAD job for YouTube URL")
    else:
        job_type = 'transcribe'
        app.logger.info(f"Creating TRANSCRIBE job for local file")

    # Save to database
    try:
        conn = get_db()
        now = datetime.now().isoformat()
        app.logger.debug(f"Inserting job into database - ID: {job_id}, Status: queued, Type: {job_type}")

        conn.execute('''INSERT INTO jobs (id, url, status, created_at, updated_at, parameters, job_type, parent_job_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (job_id, url, 'queued', now, now, json.dumps(parameters), job_type, None))
        conn.commit()

        # Verify insertion
        verify_cursor = conn.execute('SELECT id, status FROM jobs WHERE id = ?', (job_id,))
        verify_row = verify_cursor.fetchone()
        if verify_row:
            app.logger.info(f"✓ Job inserted into database: {dict(verify_row)}")
        else:
            app.logger.error(f"✗ Job NOT found in database after insert!")

        conn.close()
    except Exception as e:
        app.logger.error(f"✗ Database insertion failed: {e}", exc_info=True)
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    # Start background job with error handling
    try:
        app.logger.info(f"Creating background thread for job {job_id}, type: {job_type}")
        thread = threading.Thread(target=run_job, args=(job_id, url, parameters, job_type), daemon=True)
        thread.start()
        app.logger.info(f"✓ Thread started successfully for job {job_id}")
        app.logger.debug(f"   Thread ID: {thread.ident}, Daemon: {thread.daemon}, Alive: {thread.is_alive()}")
    except Exception as e:
        app.logger.error(f"✗ Failed to start job thread: {e}", exc_info=True)
        update_job_status(job_id, 'failed', 0, str(e))
        return jsonify({'error': f'Failed to start job: {str(e)}'}), 500

    app.logger.info(f"Returning response - Job ID: {job_id}, Status: queued")
    app.logger.info("="*60)

    # Emit socket event for immediate UI update with full job data
    try:
        socketio.emit('job_created', {
            'id': job_id,
            'url': url,
            'status': 'queued',
            'progress': 0,
            'created_at': now,
            'updated_at': now,
            'parameters': json.dumps(parameters),
            'job_type': job_type,
            'parent_job_id': None,
            'result': None,
            'error': None
        })
        app.logger.debug(f"Emitted job_created event for {job_id}")
    except Exception as e:
        app.logger.warning(f"Failed to emit job creation event: {e}")

    return jsonify({'job_id': job_id, 'status': 'queued'})


def auto_cleanup_subtitles(url, parameters):
    """Auto-cleanup generated subtitle files"""
    from pathlib import Path
    import srt_cleanup

    # Determine where to look for SRT files
    source_type = parameters.get('source_type', 'youtube')

    if source_type == 'upload' and url.startswith('file://'):
        # For uploaded files, SRT will be next to the video file
        file_path = url.replace('file://', '')
        srt_path = file_path.replace('.mp4', '.srt').replace('.mkv', '.srt').replace('.avi', '.srt')

        if os.path.exists(srt_path):
            srt_files = [srt_path]
        else:
            return None
    else:
        # For YouTube, SRT files are in yt_downloads
        download_dir = Path(app.config['DOWNLOAD_FOLDER'])
        # Find recently created SRT files (within last 5 minutes)
        import time
        cutoff_time = time.time() - 300  # 5 minutes ago
        srt_files = [
            str(f) for f in download_dir.rglob('*.srt')
            if f.stat().st_mtime > cutoff_time and '_clean' not in f.name
        ]

    if not srt_files:
        return '✨ No subtitle files found for cleanup'

    # Load filters from config
    filters = srt_cleanup.load_custom_filters('config.yaml')

    # Clean each file
    total_shortened = 0
    total_removed = 0
    files_cleaned = 0

    for srt_file in srt_files:
        try:
            # Clean the file (overwrites original)
            segments = srt_cleanup.load_srt(srt_file)

            clean_segments = []
            removed = 0
            shortened = 0

            for seg in segments:
                import copy
                seg_copy = copy.deepcopy(seg)
                result_seg, action, reason = srt_cleanup.clean_segment_text(seg_copy, filters)

                if action == 'kept':
                    clean_segments.append(seg_copy)
                elif action == 'shortened':
                    clean_segments.append(result_seg)
                    shortened += 1
                elif action == 'removed':
                    removed += 1

            # Save cleaned version (overwrite original)
            srt_cleanup.save_srt(clean_segments, srt_file)

            total_shortened += shortened
            total_removed += removed
            files_cleaned += 1

        except Exception as e:
            continue

    # Return summary
    return f'''✨ Auto-Cleanup Results:
   📄 Files processed: {files_cleaned}
   ✂️ Patterns shortened: {total_shortened}
   🗑️ Segments removed: {total_removed}
   💾 Files updated in place'''


def setup_job_logging(job_id):
    """Create a dedicated log file for a specific job"""
    import logging

    # Create logs/jobs directory if it doesn't exist
    log_dir = Path('logs/jobs')
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create job-specific log file
    log_file = log_dir / f'job_{job_id}.log'

    # Create a dedicated logger for this job
    job_logger = logging.getLogger(f'job_{job_id}')
    job_logger.setLevel(logging.INFO)
    job_logger.handlers = []  # Clear any existing handlers

    # Create file handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add handler to logger
    job_logger.addHandler(file_handler)

    return job_logger, log_file


def run_job(job_id, url, parameters, job_type):
    """Job router - dispatches to appropriate handler based on job_type"""
    app.logger.info(f"Job router: {job_id}, type: {job_type}")

    if job_type == 'download':
        run_download_job(job_id, url, parameters)
    elif job_type == 'transcribe':
        run_transcription_job(job_id, url, parameters)
    elif job_type == 'translate':
        # Translation job is handled differently (called directly from endpoint)
        pass
    elif job_type == 'transcode':
        # Transcode job is handled differently (called directly from endpoint)
        pass
    else:
        app.logger.error(f"Unknown job type: {job_type}")
        update_job_status(job_id, 'failed', 0, None, f"Unknown job type: {job_type}")


def create_transcription_job(parent_job_id, video_path, parameters):
    """Create a transcription job for a downloaded video"""
    import uuid

    job_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    # Extract video title from filename
    video_title = os.path.splitext(os.path.basename(video_path))[0]
    import re
    video_title = re.sub(r'\s*\[[a-zA-Z0-9_-]{11}\]$', '', video_title)
    video_title = video_title.strip() or "Downloaded Video"

    # Update parameters with video title and file path
    params = parameters.copy()
    params['video_title'] = video_title
    params['source_type'] = 'existing'

    # Convert local file path to file:// URL
    file_url = f"file://{video_path}"

    app.logger.info(f"Creating transcription job {job_id} for video: {video_title}")

    try:
        conn = get_db()
        conn.execute('''INSERT INTO jobs (id, url, status, created_at, updated_at, parameters, job_type, parent_job_id, video_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (job_id, file_url, 'queued', now, now, json.dumps(params), 'transcribe', parent_job_id, video_path))
        conn.commit()
        conn.close()

        # Emit socketio event to notify UI of new job
        try:
            socketio.emit('job_created', {
                'id': job_id,
                'url': file_url,
                'status': 'queued',
                'progress': 0,
                'created_at': now,
                'updated_at': now,
                'parameters': json.dumps(params),
                'job_type': 'transcribe',
                'parent_job_id': parent_job_id,
                'result': None,
                'error': None
            })
            app.logger.debug(f"Emitted job_created event for new transcription job {job_id}")
        except Exception as emit_error:
            app.logger.warning(f"Failed to emit socketio event: {emit_error}")

        # Start transcription job in background
        thread = threading.Thread(target=run_transcription_job, args=(job_id, file_url, params), daemon=True)
        thread.start()

        app.logger.info(f"✓ Transcription job {job_id} created and started, thread: {thread.ident}")
        return job_id

    except Exception as e:
        app.logger.error(f"Failed to create transcription job: {e}", exc_info=True)
        import traceback
        app.logger.error(traceback.format_exc())
        return None


def run_download_job(job_id, url, parameters):
    """Run download-only job for YouTube videos"""
    # Set up dedicated logging for this job
    job_logger, log_file = setup_job_logging(job_id)

    job_logger.info("="*60)
    job_logger.info(f"DOWNLOAD JOB STARTING: {job_id}")
    job_logger.info(f"URL: {url}")
    job_logger.info(f"Parameters: {json.dumps(parameters, indent=2)}")
    job_logger.info("="*60)

    # Update status to running
    update_job_status(job_id, 'running', 5, '📥 Starting download...')

    # Use download directory from config
    download_dir = parameters.get('download_dir', 'yt_downloads')
    os.makedirs(download_dir, exist_ok=True)

    if YTDLP_AVAILABLE:
        # Use direct yt-dlp Python API (new method)
        job_logger.info("Using direct yt-dlp Python API")

        downloaded_files = []

        # Progress hook for yt-dlp
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    if 'downloaded_bytes' in d and 'total_bytes' in d:
                        percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    elif '_percent_str' in d:
                        percent_str = d['_percent_str'].strip().replace('%', '')
                        percent = float(percent_str)
                    else:
                        percent = 0

                    speed_str = d.get('_speed_str', 'N/A')
                    eta_str = d.get('_eta_str', 'N/A')

                    message = f"📥 Downloading: {percent:.1f}%\nSpeed: {speed_str}\nETA: {eta_str}"
                    update_job_status(job_id, 'running', int(percent), message)

                except Exception as e:
                    job_logger.debug(f"Progress parsing error: {e}")

            elif d['status'] == 'finished':
                filename = d.get('filename', '')
                if filename and filename not in downloaded_files:
                    downloaded_files.append(filename)
                    job_logger.info(f"✓ Downloaded: {filename}")

        # Configure yt-dlp options
        cookie_file = parameters.get('cookie_file')
        outtmpl = os.path.join(download_dir, '%(title)s [%(id)s].%(ext)s')

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'merge_output_format': 'mp4',
            'outtmpl': outtmpl,
            'progress_hooks': [progress_hook],
            'quiet': False,
            'no_warnings': False,
            'logger': job_logger,
        }

        if cookie_file and os.path.exists(cookie_file):
            ydl_opts['cookiefile'] = cookie_file

        job_logger.info(f"yt-dlp options: {json.dumps({k: str(v) for k, v in ydl_opts.items() if k != 'logger'}, indent=2)}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                job_logger.info(f"Starting download: {url}")
                info = ydl.extract_info(url, download=True)

                # Handle playlist vs single video
                if 'entries' in info:
                    # Playlist
                    job_logger.info(f"Playlist detected with {len(info['entries'])} videos")
                    for entry in info['entries']:
                        if entry:
                            filename = ydl.prepare_filename(entry)
                            if filename and filename not in downloaded_files:
                                downloaded_files.append(filename)
                else:
                    # Single video
                    filename = ydl.prepare_filename(info)
                    if filename and filename not in downloaded_files:
                        downloaded_files.append(filename)

                job_logger.info(f"✓ Download completed successfully")
                job_logger.info(f"Downloaded {len(downloaded_files)} file(s)")

                # Create transcription jobs for each downloaded file
                transcription_jobs = []
                for video_path in downloaded_files:
                    if os.path.exists(video_path):
                        job_logger.info(f"Creating transcription job for: {video_path}")
                        transcribe_job_id = create_transcription_job(job_id, video_path, parameters)
                        if transcribe_job_id:
                            transcription_jobs.append(transcribe_job_id)
                            job_logger.info(f"✓ Created transcription job: {transcribe_job_id}")
                    else:
                        job_logger.warning(f"File does not exist: {video_path}")

                result_message = f"✅ Download complete!\n📥 Downloaded {len(downloaded_files)} video(s)\n🎙️ Created {len(transcription_jobs)} transcription job(s)"
                update_job_status(job_id, 'completed', 100, result_message)

                job_logger.info("="*60)
                job_logger.info("DOWNLOAD JOB COMPLETED")
                job_logger.info("="*60)
                return

        except Exception as e:
            job_logger.error(f"Download failed: {e}", exc_info=True)
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
            update_job_status(job_id, 'failed', 0, None, error_msg)

            job_logger.info("="*60)
            job_logger.info("DOWNLOAD JOB FAILED")
            job_logger.info("="*60)
            return

    # Fallback to subprocess if yt-dlp API not available
    else:
        job_logger.info("Using subprocess fallback (yt-dlp CLI)")
        import subprocess
        import sys

        python_exe = sys.executable
        cookie_file = parameters.get('cookie_file')
        outtmpl = os.path.join(download_dir, '%(title)s [%(id)s].%(ext)s')

        cmd = [
            python_exe, '-m', 'yt_dlp',
            '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            '--merge-output-format', 'mp4',
            '--output', outtmpl,
            '--progress',
            '--newline',
            url
        ]

        if cookie_file and os.path.exists(cookie_file):
            cmd.extend(['--cookies', cookie_file])

        job_logger.info(f"Executing command: {' '.join(cmd)}")

        try:
            # Run download process
            import os as os_module
            env = os_module.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env
            )

            output_lines = []
            downloaded_files = []

            for line in process.stdout:
                output_lines.append(line)
                job_logger.info(f"OUTPUT: {line.strip()}")

                # Parse download progress
                if '[download]' in line and '%' in line:
                    try:
                        import re
                        match = re.search(r'\[download\]\s+(\d+\.?\d*)%', line)
                        if match:
                            download_pct = float(match.group(1))
                            phase_message = f"📥 Downloading: {download_pct:.1f}%\n\n{line.strip()}"
                            update_job_status(job_id, 'running', int(download_pct), phase_message)
                    except Exception as e:
                        job_logger.debug(f"Failed to parse progress: {e}")

                # Detect completed downloads - multiple patterns
                if '[download] Destination:' in line or 'has already been downloaded' in line:
                    # Extract file path from output
                    import re
                    match = re.search(r'Destination:\s+(.+?)(?:\r|\n|$)', line)
                    if match:
                        file_path = match.group(1).strip()
                        if file_path not in downloaded_files:
                            downloaded_files.append(file_path)
                            job_logger.info(f"Detected download: {file_path}")

                # Also detect merged files (after video+audio merge)
                if '[Merger] Merging formats into' in line or '[ExtractAudio]' in line:
                    import re
                    match = re.search(r'into\s+"(.+?)"', line)
                    if match:
                        file_path = match.group(1).strip()
                        if file_path not in downloaded_files:
                            downloaded_files.append(file_path)
                            job_logger.info(f"Detected merged file: {file_path}")

            process.wait()
            job_logger.info(f"Download process completed, return code: {process.returncode}")

            if process.returncode == 0:
                job_logger.info(f"✓ Download completed successfully")
                job_logger.info(f"Detected {len(downloaded_files)} file(s) from output")

                # If no files detected from output, scan download directory for recent files
                if len(downloaded_files) == 0:
                    job_logger.warning("No files detected from output, scanning download directory...")
                    import time
                    current_time = time.time()
                    for root, dirs, files in os.walk(download_dir):
                        for file in files:
                            if file.endswith('.mp4') or file.endswith('.mkv') or file.endswith('.webm'):
                                file_path = os.path.join(root, file)
                                # Check if file was modified in last 5 minutes
                                if current_time - os.path.getmtime(file_path) < 300:
                                    downloaded_files.append(file_path)
                                    job_logger.info(f"Found recent file: {file_path}")

                job_logger.info(f"Total files to transcribe: {len(downloaded_files)}")

                # Create transcription jobs for each downloaded file
                transcription_jobs = []
                for video_path in downloaded_files:
                    if os.path.exists(video_path):
                        job_logger.info(f"Creating transcription job for: {video_path}")
                        transcribe_job_id = create_transcription_job(job_id, video_path, parameters)
                        if transcribe_job_id:
                            transcription_jobs.append(transcribe_job_id)
                            job_logger.info(f"✓ Created transcription job: {transcribe_job_id}")
                    else:
                        job_logger.warning(f"File does not exist: {video_path}")

                result_message = f"✅ Download complete!\n📥 Downloaded {len(downloaded_files)} video(s)\n🎙️ Created {len(transcription_jobs)} transcription job(s)"
                update_job_status(job_id, 'completed', 100, result_message)

                job_logger.info("="*60)
                job_logger.info("DOWNLOAD JOB COMPLETED")
                job_logger.info("="*60)
            else:
                job_logger.error(f"Download failed with return code {process.returncode}")
                update_job_status(job_id, 'failed', 0, None, '\n'.join(output_lines[-20:]))

                job_logger.info("="*60)
                job_logger.info("DOWNLOAD JOB FAILED")
                job_logger.info("="*60)

        except Exception as e:
            job_logger.error(f"Download job failed with exception: {type(e).__name__}: {str(e)}", exc_info=True)
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
            update_job_status(job_id, 'failed', 0, None, error_msg)

            job_logger.info("="*60)
            job_logger.info("DOWNLOAD JOB FAILED WITH EXCEPTION")
            job_logger.info("="*60)


def run_transcription_job(job_id, url, parameters):
    """Run transcription job in background"""
    import subprocess
    import sys

    # Set up dedicated logging for this job
    job_logger, log_file = setup_job_logging(job_id)

    job_logger.info("="*60)
    job_logger.info(f"TRANSCRIPTION JOB STARTING: {job_id}")
    job_logger.info(f"Thread ID: {threading.current_thread().ident}")
    job_logger.info(f"URL: {url}")
    job_logger.info(f"Parameters: {json.dumps(parameters, indent=2)}")
    job_logger.info(f"Log file: {log_file}")

    # Also log to main app logger
    app.logger.info(f"Job {job_id} starting - dedicated log: {log_file}")

    # Update status to running with initial progress
    job_logger.info(f"Setting job status to 'running'")
    update_job_status(job_id, 'running', 5, '⚙️ Initializing job...')

    # Use the current Python interpreter (from virtual environment)
    python_exe = sys.executable
    job_logger.info(f"Using Python interpreter: {python_exe}")

    # Detect if YouTube URL is a playlist or single video
    source_type = parameters.get('source_type', 'youtube')
    is_playlist = False
    if source_type == 'youtube':
        # Check if URL contains playlist indicators
        if 'playlist?' in url or ('list=' in url and 'watch' in url):
            is_playlist = True
            job_logger.info(f"Detected PLAYLIST URL")
        else:
            job_logger.info(f"Detected SINGLE VIDEO URL")

    # Handle file:// URLs (uploaded files or existing files)
    source_type = parameters.get('source_type', 'youtube')
    if source_type in ('upload', 'existing') and url.startswith('file://'):
        file_path = url.replace('file://', '')

        if TRANSCRIPTION_AVAILABLE:
            # Use direct function call (new method)
            job_logger.info("Using direct transcribe_file() function call")

            def progress_callback(percent, message):
                """Progress callback for transcribe_file"""
                job_logger.info(f"[{percent}%] {message}")
                update_job_status(job_id, 'running', int(percent), f'🎙️ {message}')

            try:
                output_path, segment_count = transcribe_file(
                    input_path=file_path,
                    model_name=parameters.get('model', 'large-v3'),
                    device=parameters.get('device', 'cuda'),
                    compute_type=parameters.get('compute_type', 'float16'),
                    language=parameters.get('language', 'sr'),
                    beam_size=parameters.get('beam_size', 12),
                    vad_filter=parameters.get('vad_filter', False),
                    temperature=parameters.get('temperature', 0.2),
                    no_speech_threshold=parameters.get('no_speech_threshold', 0.1),
                    compression_threshold=parameters.get('compression_threshold', 2.8),
                    chunk_length=parameters.get('chunk_length'),
                    progress_callback=progress_callback,
                    job_id=job_id,
                    active_processes_dict=active_job_processes
                )

                result_message = f"✅ Transcription complete!\n\n{segment_count} segments saved to:\n{os.path.basename(output_path)}"
                update_job_status(job_id, 'completed', 100, result_message)

                job_logger.info("="*60)
                job_logger.info("TRANSCRIPTION JOB COMPLETED SUCCESSFULLY")
                job_logger.info(f"Output: {output_path}")
                job_logger.info(f"Segments: {segment_count}")
                job_logger.info("="*60)

                # Auto-cleanup if requested
                if parameters.get('auto_cleanup', False):
                    try:
                        auto_cleanup_subtitles(url, parameters)
                    except Exception as cleanup_error:
                        job_logger.warning(f"Auto-cleanup failed: {cleanup_error}")

                # Force cleanup of resources to release file handles
                import gc
                gc.collect()
                job_logger.debug("Released file handles and cleaned up resources")

                return

            except Exception as e:
                job_logger.error(f"Direct transcription failed: {e}", exc_info=True)
                import traceback
                error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
                update_job_status(job_id, 'failed', 0, None, error_msg)

                job_logger.info("="*60)
                job_logger.info("TRANSCRIPTION JOB FAILED")
                job_logger.info("="*60)
                return

        # Fallback to subprocess if direct call not available
        else:
            job_logger.info("Using subprocess fallback (faster_whisper_latin.py)")
            cmd = [
                python_exe, 'faster_whisper_latin.py',
                file_path,
                '--model', parameters.get('model', 'large-v3'),
                '--device', parameters.get('device', 'cuda')
            ]

            # Add language parameter for single file
            if parameters.get('language') and parameters['language'] != 'auto':
                cmd.extend(['--language', parameters['language']])

            # Add beam size
            if parameters.get('beam_size'):
                cmd.extend(['--beam', str(parameters['beam_size'])])

            # Add VAD filter
            if parameters.get('vad_filter'):
                cmd.extend(['--vad', 'True'])

            # Add compute type
            if parameters.get('compute_type'):
                cmd.extend(['--compute', parameters['compute_type']])

            # Add temperature
            if parameters.get('temperature') is not None:
                cmd.extend(['--temp', str(parameters['temperature'])])
    else:
        # For YouTube URLs, use direct function calls
        if is_playlist:
            # Playlists should go through download job system
            # This code path shouldn't be reached in normal operation
            job_logger.warning("Playlist detected in transcription job - this should have been handled by download job")
            error_msg = "Playlists should be submitted as download jobs, not transcription jobs"
            update_job_status(job_id, 'failed', 0, None, error_msg)

            job_logger.info("="*60)
            job_logger.info("TRANSCRIPTION JOB FAILED - PLAYLIST")
            job_logger.info("="*60)
            return
        else:
            # Use transcribe_single_video for single videos
            if TRANSCRIBE_SINGLE_AVAILABLE:
                job_logger.info("Using direct transcribe_single_video() function call")

                def progress_callback(percent, message):
                    """Progress callback for transcribe_single_video"""
                    job_logger.info(f"[{percent}%] {message}")
                    update_job_status(job_id, 'running', int(percent), message)

                try:
                    # Build transcription parameters
                    transcription_params = {
                        'model': parameters.get('model', 'large-v3'),
                        'device': parameters.get('device', 'cuda'),
                        'compute_type': parameters.get('compute_type', 'float16'),
                        'language': parameters.get('language', 'sr'),
                        'beam_size': parameters.get('beam_size', 12),
                        'vad_filter': parameters.get('vad_filter', False),
                        'temperature': parameters.get('temperature', 0.2),
                        'no_speech_threshold': parameters.get('no_speech_threshold', 0.1),
                        'compression_threshold': parameters.get('compression_threshold', 2.8),
                        'chunk_length': parameters.get('chunk_length', None),
                    }

                    result = transcribe_single_video(
                        video_url=url,
                        download_dir=parameters.get('download_dir', 'yt_downloads'),
                        cookie_file=parameters.get('cookie_file'),
                        force=False,
                        transcription_params=transcription_params,
                        progress_callback=progress_callback
                    )

                    result_message = f"✅ Transcription complete!\n\n{result['video_title']}\n\nSubtitle: {os.path.basename(result['srt_path'])}"
                    update_job_status(job_id, 'completed', 100, result_message)

                    job_logger.info("="*60)
                    job_logger.info("TRANSCRIPTION JOB COMPLETED SUCCESSFULLY")
                    job_logger.info(f"Video: {result['video_path']}")
                    job_logger.info(f"Subtitle: {result['srt_path']}")
                    job_logger.info("="*60)

                    # Auto-cleanup if requested
                    if parameters.get('auto_cleanup', False):
                        try:
                            # Convert result to file:// URL for cleanup
                            file_url = f"file://{result['video_path']}"
                            auto_cleanup_subtitles(file_url, parameters)
                        except Exception as cleanup_error:
                            job_logger.warning(f"Auto-cleanup failed: {cleanup_error}")

                    return

                except Exception as e:
                    job_logger.error(f"Direct transcription failed: {e}", exc_info=True)
                    import traceback
                    error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
                    update_job_status(job_id, 'failed', 0, None, error_msg)

                    job_logger.info("="*60)
                    job_logger.info("TRANSCRIPTION JOB FAILED")
                    job_logger.info("="*60)
                    return

            # Fallback to subprocess if direct call not available
            else:
                job_logger.info("Using subprocess fallback (transcribe_single.py)")
                cmd = [
                    python_exe, 'transcribe_single.py',
                    url
                ]

                # Add cookie file if provided
                if parameters.get('cookie_file'):
                    cmd.extend(['--cookies', parameters['cookie_file']])

                # Add transcriber arguments
                transcriber_args = []

                if parameters.get('model'):
                    transcriber_args.extend(['--model', parameters['model']])

                if parameters.get('device'):
                    transcriber_args.extend(['--device', parameters['device']])

                if parameters.get('language') and parameters['language'] != 'auto':
                    transcriber_args.extend(['--language', parameters['language']])

                if parameters.get('beam_size'):
                    transcriber_args.extend(['--beam', str(parameters['beam_size'])])

                if parameters.get('vad_filter'):
                    transcriber_args.extend(['--vad', 'True'])

                if parameters.get('compute_type'):
                    transcriber_args.extend(['--compute', parameters['compute_type']])

                if parameters.get('temperature') is not None:
                    transcriber_args.extend(['--temp', str(parameters['temperature'])])

                # Add all transcriber args
                if transcriber_args:
                    cmd.append('--transcriber-args')
                    cmd.extend(transcriber_args)

    try:
        # Log the full command for debugging
        job_logger.info(f"Executing command: {' '.join(cmd)}")

        # Update progress before starting
        job_logger.info("Starting transcription process...")
        update_job_status(job_id, 'running', 10, '📥 Preparing to download...')

        # Run process with UTF-8 encoding
        # Using encoding parameter instead of universal_newlines to ensure UTF-8 on Windows
        import os as os_module
        env = os_module.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            errors='replace',  # Replace invalid characters instead of crashing
            bufsize=1,
            env=env
        )

        # Monitor progress
        output_lines = []
        last_progress = 0
        line_count = 0

        for line in process.stdout:
            output_lines.append(line)
            line_count += 1

            # Write to job log file
            job_logger.info(f"OUTPUT: {line.strip()}")

            # Try to extract progress info from different sources
            progress_updated = False

            # Pattern 0: Download progress from yt-dlp "[download] 33.9% of ..."
            # Map download to 0-33% range (download = 1/3 of total job)
            if '[download]' in line and '%' in line:
                try:
                    import re
                    # Match patterns like "[download]  33.9%" or "[download] 100.0%"
                    match = re.search(r'\[download\]\s+(\d+\.?\d*)%', line)
                    if match:
                        download_pct = float(match.group(1))
                        # Map download progress to 0-33% of overall job
                        # If download is at 100%, that's 33% of overall job
                        overall_progress = int((download_pct / 100.0) * 33)

                        if overall_progress > last_progress:
                            phase_message = f"📥 Downloading: {download_pct:.1f}%\n\n{line.strip()}"
                            job_logger.info(f"Download progress: {download_pct:.1f}% → Overall: {overall_progress}%")
                            update_job_status(job_id, 'running', overall_progress, phase_message)
                            last_progress = overall_progress
                            progress_updated = True
                except Exception as e:
                    job_logger.debug(f"Failed to parse download progress: {e}")

            # Periodic update every 20 lines to keep the UI refreshed
            if not progress_updated and line_count % 20 == 0 and last_progress < 80:
                # Gradually increase progress
                new_progress = min(last_progress + 5, 80)
                if new_progress > last_progress:
                    # Determine phase based on progress
                    if new_progress <= 33:
                        phase_icon = "📥"
                        phase_name = "Downloading"
                    else:
                        phase_icon = "🎙️"
                        phase_name = "Transcribing"

                    phase_message = f"{phase_icon} {phase_name}: {new_progress}%\n\n" + '\n'.join(output_lines[-5:])
                    job_logger.info(f"Periodic progress update: {new_progress}%")
                    update_job_status(job_id, 'running', new_progress, phase_message)
                    last_progress = new_progress
                    progress_updated = True

            # Pattern 1: Playlist progress "[3/10]"
            if '/' in line and any(emoji in line for emoji in ['🎙️', '✅', '⏭️']):
                try:
                    import re
                    match = re.search(r'\[(\d+)/(\d+)\]', line)
                    if match:
                        current, total = int(match.group(1)), int(match.group(2))
                        progress = int((current / total) * 100)
                        update_job_status(job_id, 'running', progress, '\n'.join(output_lines[-10:]))
                        last_progress = progress
                        progress_updated = True
                except:
                    pass

            # Pattern 2: Milestone-based progress for transcription phase
            # Download = 0-33%, Transcription = 34-100%
            if not progress_updated:
                line_lower = line.lower()
                if 'starting transcription' in line_lower or 'transcription started' in line_lower:
                    # Transcription starts at 34% (after download)
                    if last_progress < 34:
                        phase_message = f"🎙️ Transcribing: Starting...\n\n{line.strip()}"
                        job_logger.info("Progress milestone - Starting transcription (34%)")
                        update_job_status(job_id, 'running', 34, phase_message)
                        last_progress = 34
                elif 'processing audio' in line_lower or 'detect language' in line_lower:
                    # Audio processing at 45%
                    if last_progress < 45:
                        phase_message = f"🎙️ Transcribing: Processing audio...\n\n{line.strip()}"
                        job_logger.info("Progress milestone - Processing audio (45%)")
                        update_job_status(job_id, 'running', 45, phase_message)
                        last_progress = 45
                elif 'transcribing' in line_lower or 'segments' in line_lower:
                    # Transcribing segments at 60%
                    if last_progress < 60:
                        phase_message = f"🎙️ Transcribing: Generating segments...\n\n{line.strip()}"
                        job_logger.info("Progress milestone - Transcribing segments (60%)")
                        update_job_status(job_id, 'running', 60, phase_message)
                        last_progress = 60
                elif 'transcription complete' in line_lower or 'transcription completed' in line_lower:
                    # Transcription complete at 90%
                    if last_progress < 90:
                        phase_message = f"🎙️ Transcribing: Finalizing...\n\n{line.strip()}"
                        job_logger.info("Progress milestone - Transcription complete (90%)")
                        update_job_status(job_id, 'running', 90, phase_message)
                        last_progress = 90

        process.wait()
        job_logger.info(f"Transcription process completed, return code: {process.returncode}")

        if process.returncode == 0:
            job_logger.info("✓ Job completed successfully")
            result_output = '\n'.join(output_lines[-20:])

            # Auto-cleanup if enabled
            if parameters.get('auto_cleanup', False):
                job_logger.info("Running auto-cleanup...")
                try:
                    cleanup_result = auto_cleanup_subtitles(url, parameters)
                    if cleanup_result:
                        result_output += '\n\n' + cleanup_result
                        job_logger.info("✓ Auto-cleanup completed")
                except Exception as e:
                    job_logger.error(f"⚠ Auto-cleanup error: {e}")
                    result_output += f'\n\n⚠️ Auto-cleanup error: {str(e)}'

            update_job_status(job_id, 'completed', 100, result_output)
            job_logger.info("="*60)
            job_logger.info("JOB COMPLETED SUCCESSFULLY")
            job_logger.info("="*60)
        else:
            job_logger.warning(f"✗ Job failed with return code {process.returncode}")
            update_job_status(job_id, 'failed', 0, None, '\n'.join(output_lines[-20:]))
            job_logger.info("="*60)
            job_logger.info("JOB FAILED")
            job_logger.info("="*60)

    except Exception as e:
        job_logger.error(f"✗ Job failed with exception: {type(e).__name__}: {str(e)}", exc_info=True)
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
        update_job_status(job_id, 'failed', 0, None, error_msg)
        job_logger.info("="*60)
        job_logger.info("JOB FAILED WITH EXCEPTION")
        job_logger.info("="*60)


def run_translation_job(job_id, srt_file_path, target_lang, source_lang='auto'):
    """Run translation job for subtitle file"""
    job_logger, log_file = setup_job_logging(job_id)

    try:
        job_logger.info("="*60)
        job_logger.info(f"TRANSLATION JOB STARTED: {job_id}")
        job_logger.info(f"Source file: {srt_file_path}")
        job_logger.info(f"Source language: {source_lang}")
        job_logger.info(f"Target language: {target_lang}")
        job_logger.info("="*60)

        if not TRANSLATOR_AVAILABLE:
            error_msg = "Translation library not installed"
            job_logger.error(error_msg)
            update_job_status(job_id, 'failed', 0, None, error_msg)
            return

        # Normalize source language code
        # "default" should be treated as auto-detect
        if source_lang == 'default' or not source_lang or source_lang == '':
            source_lang = 'auto'
            job_logger.info(f"Normalized source language to 'auto'")

        # Map common language codes to Google Translate codes
        lang_map = {
            'sr': 'sr',  # Serbian
            'hr': 'hr',  # Croatian
            'bs': 'bs',  # Bosnian
            'en': 'en',  # English
            'de': 'de',  # German
            'fr': 'fr',  # French
            'es': 'es',  # Spanish
            'it': 'it',  # Italian
            'pt': 'pt',  # Portuguese
            'ru': 'ru',  # Russian
            'pl': 'pl',  # Polish
            'tr': 'tr',  # Turkish
        }

        # Validate source language if not auto
        if source_lang != 'auto' and source_lang not in lang_map:
            job_logger.warning(f"Unknown source language '{source_lang}', using auto-detect")
            source_lang = 'auto'

        # Read SRT file with encoding detection
        update_job_status(job_id, 'running', 10, '📖 Reading subtitle file...')
        job_logger.info("Reading SRT file...")

        # Try different encodings
        encodings_to_try = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1', 'iso-8859-1', 'cp1251']
        srt_content = None
        used_encoding = None

        for encoding in encodings_to_try:
            try:
                with open(srt_file_path, 'r', encoding=encoding) as f:
                    srt_content = f.read()
                used_encoding = encoding
                job_logger.info(f"Successfully read file with encoding: {encoding}")
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if srt_content is None:
            error_msg = "Failed to read subtitle file - unsupported encoding"
            job_logger.error(error_msg)
            update_job_status(job_id, 'failed', 0, None, error_msg)
            return

        try:
            import pysrt
            # Try to parse with pysrt using detected encoding
            try:
                subs = pysrt.open(srt_file_path, encoding=used_encoding)
                segments = []
                for sub in subs:
                    segments.append({
                        'index': sub.index,
                        'time': f"{sub.start} --> {sub.end}",
                        'text': sub.text
                    })
                job_logger.info(f"Loaded {len(segments)} subtitle segments using pysrt")
            except Exception as e:
                job_logger.warning(f"pysrt parsing failed: {e}, falling back to manual parsing")
                raise ImportError  # Fall back to manual parsing
        except ImportError:
            # Manual SRT parsing
            job_logger.info("Using manual SRT parsing")

            # Simple SRT parsing
            segments = []
            blocks = srt_content.strip().split('\n\n')
            for block in blocks:
                lines = block.split('\n')
                if len(lines) >= 3:
                    # Extract text (everything after the timestamp line)
                    text = '\n'.join(lines[2:])
                    segments.append({
                        'index': lines[0],
                        'time': lines[1],
                        'text': text
                    })

            job_logger.info(f"Parsed {len(segments)} subtitle segments manually")

        # Initialize translator
        update_job_status(job_id, 'running', 15, '🌐 Initializing translator...')
        translator = Translator()

        # Translate segments
        translated_segments = []
        total = len(segments)

        for i, seg in enumerate(segments):
            progress = 15 + int((i / total) * 80)  # 15% to 95%
            percent_done = int((i / total) * 100)

            update_job_status(
                job_id, 'running', progress,
                f'🌐 Translating segments: {i+1}/{total} ({percent_done}%)'
            )

            try:
                # Translate text
                result = translator.translate(seg['text'], src=source_lang, dest=target_lang)
                translated_text = result.text

                # Detect source language from first segment if auto
                if source_lang == 'auto' and i == 0:
                    source_lang = result.src
                    job_logger.info(f"Detected source language: {source_lang}")

                translated_segments.append({
                    'index': seg['index'],
                    'time': seg['time'],
                    'text': translated_text
                })

                # Log without including actual text to avoid encoding issues in logs
                job_logger.info(f"[{i+1}/{total}] Segment translated successfully")

            except Exception as e:
                job_logger.warning(f"Translation error for segment {i+1}: {e}, keeping original")
                translated_segments.append(seg)

        # Generate output filename with language suffix
        update_job_status(job_id, 'running', 95, '💾 Saving translated subtitle...')

        base_name = os.path.splitext(srt_file_path)[0]

        # Remove existing language suffix if present (both 2-letter and 3-letter codes)
        # e.g., "video.rus" -> "video", "video.sr" -> "video"
        parts = base_name.split('.')
        if len(parts) > 1:
            last_part = parts[-1].lower()
            # Check if last part is a language code (2 or 3 letters)
            if len(last_part) in [2, 3] and last_part.isalpha():
                # List of common language codes to detect
                common_lang_codes = [
                    'en', 'eng', 'es', 'spa', 'fr', 'fra', 'fre', 'de', 'deu', 'ger',
                    'it', 'ita', 'pt', 'por', 'pl', 'pol', 'tr', 'tur', 'ru', 'rus',
                    'nl', 'nld', 'dut', 'cs', 'ces', 'cze', 'ar', 'ara', 'zh', 'zho',
                    'chi', 'ja', 'jpn', 'ko', 'kor', 'hi', 'hin', 'sv', 'swe', 'da',
                    'dan', 'no', 'nor', 'fi', 'fin', 'uk', 'ukr', 'el', 'ell', 'gre',
                    'ro', 'ron', 'rum', 'hu', 'hun', 'sr', 'srp', 'hr', 'hrv', 'bg',
                    'bul', 'sk', 'slk', 'slo', 'sl', 'slv', 'lt', 'lit', 'lv', 'lav',
                    'et', 'est', 'ga', 'gle', 'vi', 'vie', 'th', 'tha', 'id', 'ind',
                    'ms', 'msa', 'may', 'he', 'heb', 'fa', 'fas', 'per', 'ca', 'cat'
                ]
                if last_part in common_lang_codes:
                    base_name = '.'.join(parts[:-1])
                    job_logger.info(f"Removed language suffix '{last_part}' from filename")

        output_path = f"{base_name}.{target_lang}.srt"

        job_logger.info(f"Writing translated SRT to: {output_path}")

        # Write translated SRT
        with open(output_path, 'w', encoding='utf-8') as f:
            for seg in translated_segments:
                f.write(f"{seg['index']}\n")
                f.write(f"{seg['time']}\n")
                f.write(f"{seg['text']}\n\n")

        # Complete
        lang_name = LANGUAGE_NAMES.get(target_lang, target_lang.upper())
        result_msg = f"✅ Translation complete!\n\nTranslated {len(segments)} segments\n{source_lang.upper()} → {lang_name}\n\nOutput: {os.path.basename(output_path)}"

        update_job_status(job_id, 'completed', 100, result_msg)

        job_logger.info("="*60)
        job_logger.info(f"TRANSLATION JOB COMPLETED: {job_id}")
        job_logger.info(f"Output file: {output_path}")
        job_logger.info("="*60)

    except Exception as e:
        error_msg = f"Translation failed: {str(e)}"
        job_logger.error(error_msg, exc_info=True)
        update_job_status(job_id, 'failed', 0, None, error_msg)


def run_transcode_job(job_id, input_path, output_path):
    """Run video transcoding job to convert to MP4"""
    job_logger, log_file = setup_job_logging(job_id)

    try:
        job_logger.info("="*60)
        job_logger.info(f"TRANSCODE JOB STARTED: {job_id}")
        job_logger.info(f"Input file: {input_path}")
        job_logger.info(f"Output file: {output_path}")
        job_logger.info("="*60)

        # Check ffmpeg availability
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            error_msg = "FFmpeg not found. Please install FFmpeg to use transcoding."
            job_logger.error(error_msg)
            update_job_status(job_id, 'failed', 0, None, error_msg)
            return

        update_job_status(job_id, 'running', 5, '🎬 Starting transcoding...')

        # Get video duration for progress calculation
        job_logger.info("Getting video duration...")
        try:
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_path
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            job_logger.info(f"Video duration: {duration:.2f} seconds")
        except Exception as e:
            job_logger.warning(f"Could not get video duration: {e}, progress will be approximate")
            duration = None

        # Transcode command using H.264 codec for maximum compatibility
        cmd = [
            'ffmpeg', '-y',  # Overwrite output
            '-i', input_path,
            '-c:v', 'libx264',  # H.264 video codec
            '-preset', 'medium',  # Balance between speed and compression
            '-crf', '23',  # Constant Rate Factor (quality: 0-51, lower is better)
            '-c:a', 'aac',  # AAC audio codec
            '-b:a', '128k',  # Audio bitrate
            '-movflags', '+faststart',  # Enable streaming
            '-progress', 'pipe:1',  # Output progress to stdout
            output_path
        ]

        job_logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        update_job_status(job_id, 'running', 10, '🔄 Transcoding video...')

        # Start FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )

        # Register process for cancellation
        if job_id in active_job_processes:
            pass  # Already registered
        else:
            active_job_processes[job_id] = process

        # Parse FFmpeg progress output
        import re
        time_pattern = re.compile(r'out_time_ms=(\d+)')
        last_progress = 10

        for line in process.stdout:
            # Check if job was cancelled
            conn = get_db()
            cursor = conn.execute('SELECT status FROM jobs WHERE id = ?', (job_id,))
            job_status = cursor.fetchone()
            conn.close()

            if job_status and job_status[0] == 'cancelled':
                job_logger.info("Job cancelled by user, terminating FFmpeg")
                process.terminate()
                break

            # Parse time progress
            match = time_pattern.search(line)
            if match and duration:
                time_ms = int(match.group(1))
                time_seconds = time_ms / 1000000.0
                progress_pct = min((time_seconds / duration) * 100, 99)
                # Map to 10-95% range
                progress = int(10 + (progress_pct * 0.85))

                if progress > last_progress:
                    update_job_status(
                        job_id, 'running', progress,
                        f'🔄 Transcoding: {time_seconds:.1f}s / {duration:.1f}s ({progress}%)'
                    )
                    last_progress = progress

        # Wait for process to complete
        process.wait()

        # Remove from active processes
        active_job_processes.pop(job_id, None)

        # Check result
        if process.returncode == 0:
            # Success
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            result_msg = f"✅ Transcoding complete!\n\nOutput: {os.path.basename(output_path)}\nSize: {file_size:.2f} MB\n\nThe MP4 file is ready to play in your browser."

            update_job_status(job_id, 'completed', 100, result_msg)
            job_logger.info("="*60)
            job_logger.info(f"TRANSCODE JOB COMPLETED: {job_id}")
            job_logger.info(f"Output file: {output_path}")
            job_logger.info("="*60)
        else:
            # Error
            stderr_output = process.stderr.read() if process.stderr else ""
            error_msg = f"FFmpeg transcoding failed (exit code {process.returncode})"
            job_logger.error(error_msg)
            job_logger.error(f"FFmpeg stderr: {stderr_output[:500]}")
            update_job_status(job_id, 'failed', last_progress, None, error_msg)

    except Exception as e:
        error_msg = f"Transcoding failed: {str(e)}"
        job_logger.error(error_msg, exc_info=True)
        update_job_status(job_id, 'failed', 0, None, error_msg)


def cleanup_wav_file(job_id):
    """Delete generated WAV file for a job if it exists"""
    try:
        # Get job URL from database
        conn = get_db()
        cursor = conn.execute('SELECT url FROM jobs WHERE id = ?', (job_id,))
        job = cursor.fetchone()
        conn.close()

        if not job:
            return

        url = job[0]

        # Only cleanup for file:// URLs (uploaded/existing files)
        if url and url.startswith('file://'):
            file_path = url.replace('file://', '')
            if os.path.exists(file_path):
                # Construct WAV filename (same logic as preprocess_audio)
                base, _ = os.path.splitext(file_path)
                wav_file = base + "_clean.wav"

                if os.path.exists(wav_file):
                    try:
                        os.remove(wav_file)
                        app.logger.info(f"✓ Deleted generated WAV file: {wav_file}")
                    except Exception as e:
                        app.logger.warning(f"Could not delete WAV file {wav_file}: {e}")
    except Exception as e:
        app.logger.warning(f"Error during WAV cleanup for job {job_id}: {e}")


def update_job_status(job_id, status, progress, result=None, error=None):
    """Update job status in database and notify clients"""
    app.logger.debug(f"update_job_status called: job_id={job_id}, status={status}, progress={progress}")

    try:
        conn = get_db()
        now = datetime.now().isoformat()

        app.logger.debug(f"Updating job {job_id} in database")
        cursor = conn.execute('''UPDATE jobs SET status=?, progress=?, updated_at=?, result=?, error=?
                        WHERE id=?''',
                     (status, progress, now, result, error, job_id))

        rows_affected = cursor.rowcount
        conn.commit()

        if rows_affected > 0:
            app.logger.info(f"✓ Job {job_id} updated in DB: status={status}, progress={progress}")

            # Verify update
            verify_cursor = conn.execute('SELECT id, status, progress FROM jobs WHERE id = ?', (job_id,))
            verify_row = verify_cursor.fetchone()
            if verify_row:
                app.logger.debug(f"   Verified in DB: {dict(verify_row)}")
            else:
                app.logger.error(f"✗ Job {job_id} NOT found after update!")
        else:
            app.logger.warning(f"⚠ No rows affected when updating job {job_id}")

        conn.close()
    except Exception as e:
        app.logger.error(f"✗ Failed to update job {job_id} in database: {e}", exc_info=True)
        return

    # Clean up WAV files when jobs are cancelled or failed
    if status in ['cancelled', 'failed']:
        cleanup_wav_file(job_id)

    # Emit socket event
    try:
        app.logger.debug(f"Emitting SocketIO 'job_update' event for job {job_id}")
        socketio.emit('job_update', {
            'job_id': job_id,
            'status': status,
            'progress': progress,
            'result': result,
            'error': error
        })
        app.logger.debug(f"✓ SocketIO event emitted for job {job_id}")
    except Exception as e:
        app.logger.error(f"✗ Failed to emit SocketIO event for job {job_id}: {e}", exc_info=True)


@app.route('/api/jobs')
def get_jobs():
    """Get all jobs"""
    app.logger.debug("GET /api/jobs - Fetching all jobs")
    conn = get_db()
    jobs = conn.execute('SELECT * FROM jobs ORDER BY created_at DESC').fetchall()
    conn.close()

    jobs_list = [dict(job) for job in jobs]
    app.logger.debug(f"Returning {len(jobs_list)} jobs")

    for job in jobs_list:
        app.logger.debug(f"  Job: {job['id'][:8]}... | Status: {job['status']} | Progress: {job['progress']}%")

    return jsonify(jobs_list)


@app.route('/api/jobs/<job_id>')
def get_job(job_id):
    """Get specific job details"""
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
    conn.close()

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(dict(job))


@app.route('/api/jobs/<job_id>/logs')
def get_job_logs(job_id):
    """Get job logs from dedicated log file"""
    log_file = Path('logs/jobs') / f'job_{job_id}.log'

    if not log_file.exists():
        return jsonify({'error': 'Log file not found', 'message': 'Logs may not have been generated yet'}), 404

    try:
        # Try different encodings for log file
        encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']
        logs = None

        for encoding in encodings:
            try:
                with open(log_file, 'r', encoding=encoding, errors='replace') as f:
                    logs = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if logs is None:
            logs = "Error: Could not read log file with supported encodings"

        return jsonify({
            'job_id': job_id,
            'log_file': str(log_file),
            'logs': logs,
            'size': len(logs)
        })
    except Exception as e:
        app.logger.error(f"Error reading log file for job {job_id}: {e}")
        return jsonify({'error': f'Failed to read log file: {str(e)}'}), 500


@app.route('/api/files')
def list_files():
    """List downloaded files and folders (hierarchical structure)"""
    download_dir = Path(app.config['DOWNLOAD_FOLDER'])

    # Get optional subdirectory parameter for navigation
    subdir = request.args.get('path', '')
    current_dir = download_dir / subdir if subdir else download_dir

    if not current_dir.exists() or not current_dir.is_dir():
        return jsonify({'error': 'Directory not found'}), 404

    video_extensions = ['.mp4', '.mkv', '.avi', '.webm', '.mov']
    subtitle_extensions = ['.srt', '.vtt', '.ass']
    allowed_extensions = video_extensions + subtitle_extensions

    items = []

    # Add folders
    try:
        for item in sorted(current_dir.iterdir(), key=lambda x: x.name.lower()):
            if item.is_dir():
                # Count video and subtitle files in this folder (recursive)
                video_count = sum(1 for f in item.rglob('*') if f.is_file() and f.suffix.lower() in video_extensions)
                subtitle_count = sum(1 for f in item.rglob('*') if f.is_file() and f.suffix.lower() in subtitle_extensions)

                rel_path = item.relative_to(download_dir)
                path_str = str(rel_path).replace('\\', '/')

                folder_info = {
                    'name': item.name,
                    'path': path_str,
                    'type': 'folder',
                    'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    'video_count': video_count,
                    'subtitle_count': subtitle_count
                }
                items.append(folder_info)
    except PermissionError:
        pass

    # Add files (only videos and subtitles)
    # First pass: collect all video files
    video_files = []
    try:
        for item in sorted(current_dir.iterdir(), key=lambda x: x.name.lower()):
            if item.is_file() and item.suffix.lower() in video_extensions:
                video_files.append(item)
    except PermissionError:
        pass

    # Build set of video base names (without extension) for SRT filtering
    video_base_names = {item.stem for item in video_files}

    # Second pass: add video files with subtitle info
    for item in video_files:
        rel_path = item.relative_to(download_dir)
        path_str = str(rel_path).replace('\\', '/')

        file_info = {
            'name': item.name,
            'path': path_str,
            'size': item.stat().st_size,
            'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
            'type': item.suffix.lower()
        }

        # Check if video has subtitles (with language suffixes)
        # Look for: video.en.srt, video.es.srt, etc.
        base_name = item.stem
        parent_dir = item.parent
        subtitle_languages = []

        # Check for language-suffixed subtitles
        for srt_file in parent_dir.glob(f"{base_name}.*.srt"):
            # Extract language code from filename (e.g., "video.en.srt" -> "en")
            parts = srt_file.stem.split('.')
            if len(parts) >= 2:
                lang_code = parts[-1]
                subtitle_languages.append(lang_code)

        # Also check for subtitle without suffix (legacy support)
        legacy_srt = item.with_suffix('.srt')
        if legacy_srt.exists():
            subtitle_languages.append('default')

        file_info['has_subtitles'] = len(subtitle_languages) > 0
        file_info['subtitle_languages'] = subtitle_languages

        items.append(file_info)

    # Third pass: add standalone subtitle files (only if no matching video exists)
    try:
        for item in sorted(current_dir.iterdir(), key=lambda x: x.name.lower()):
            if item.is_file() and item.suffix.lower() in subtitle_extensions:
                # Skip this SRT if there's a video with the same base name
                if item.stem in video_base_names:
                    continue

                rel_path = item.relative_to(download_dir)
                path_str = str(rel_path).replace('\\', '/')

                file_info = {
                    'name': item.name,
                    'path': path_str,
                    'size': item.stat().st_size,
                    'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    'type': item.suffix.lower()
                }

                items.append(file_info)
    except PermissionError:
        pass

    return jsonify({
        'current_path': subdir,
        'items': items
    })


@app.route('/api/files/<path:filename>')
def download_file(filename):
    """Download or stream a file"""
    from urllib.parse import unquote
    import os

    # Debug logging
    app.logger.debug(f"🔍 File request: {filename}")

    # Decode URL-encoded filename
    filename_decoded = unquote(filename)
    app.logger.debug(f"   Decoded: {filename_decoded}")

    # Keep original with forward slashes for send_from_directory
    filename_for_send = filename_decoded

    # Normalize path separators for Windows file existence check
    filename_normalized = filename_decoded.replace('/', os.sep)
    app.logger.debug(f"   Normalized: {filename_normalized}")

    # Security: prevent directory traversal
    filename_check = os.path.normpath(filename_normalized)
    app.logger.debug(f"   Norm path: {filename_check}")

    if filename_check.startswith('..') or os.path.isabs(filename_check):
        return jsonify({'error': 'Invalid file path'}), 400

    # Check if file exists using normalized path
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename_check)
    app.logger.debug(f"   Full path: {file_path}")
    app.logger.debug(f"   Exists: {os.path.exists(file_path)}")

    if not os.path.exists(file_path):
        # List files in parent directory for debugging
        parent_dir = os.path.dirname(file_path)
        if os.path.exists(parent_dir):
            files_in_dir = os.listdir(parent_dir)
            app.logger.debug(f"   Files in {parent_dir}:")
            for f in files_in_dir[:5]:
                app.logger.debug(f"     - {f}")

        return jsonify({'error': 'File not found', 'path': filename_decoded, 'full_path': file_path}), 404

    # Check if download is explicitly requested
    force_download = request.args.get('download', 'false').lower() == 'true'

    # For video files, stream unless download is forced
    video_extensions = ['.mp4', '.mkv', '.avi', '.webm', '.mov']
    file_ext = os.path.splitext(filename_decoded)[1].lower()

    app.logger.debug(f"   Sending file with path: {filename_for_send}")
    app.logger.debug(f"   Force download: {force_download}")

    if file_ext in video_extensions and not force_download:
        # Stream video (no attachment) - use forward slash path
        return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename_for_send, as_attachment=False)
    else:
        # Download file (including forced video downloads) - use forward slash path
        return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename_for_send, as_attachment=True)


@app.route('/api/files/create-folder', methods=['POST'])
def create_folder():
    """Create a new folder in the download directory"""
    try:
        data = request.json
        folder_name = data.get('folder_name', '').strip()
        parent_path = data.get('parent_path', '').strip()

        if not folder_name:
            return jsonify({'error': 'Folder name is required'}), 400

        # Security: prevent directory traversal
        if '..' in folder_name or '/' in folder_name or '\\' in folder_name:
            return jsonify({'error': 'Invalid folder name'}), 400

        # Build full path
        if parent_path:
            parent_path = parent_path.replace('..', '').strip('/')
            full_path = Path(app.config['DOWNLOAD_FOLDER']) / parent_path / folder_name
        else:
            full_path = Path(app.config['DOWNLOAD_FOLDER']) / folder_name

        # Check if folder already exists
        if full_path.exists():
            return jsonify({'error': 'Folder already exists'}), 400

        # Create folder
        full_path.mkdir(parents=True, exist_ok=False)
        app.logger.info(f"Created folder: {full_path}")

        return jsonify({'success': True, 'path': str(full_path.relative_to(app.config['DOWNLOAD_FOLDER']))})

    except Exception as e:
        app.logger.error(f"Error creating folder: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/folders', methods=['GET'])
def list_folders():
    """List all folders in the download directory for move operations"""
    try:
        download_dir = Path(app.config['DOWNLOAD_FOLDER'])
        folders = []

        # Recursively find all folders
        for item in download_dir.rglob('*'):
            if item.is_dir():
                rel_path = item.relative_to(download_dir)
                folders.append({
                    'path': str(rel_path).replace('\\', '/'),
                    'name': item.name
                })

        # Sort by path
        folders.sort(key=lambda x: x['path'])

        return jsonify({'folders': folders})

    except Exception as e:
        app.logger.error(f"Error listing folders: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/move', methods=['POST'])
def move_item():
    """Move a file or folder to a different location"""
    try:
        data = request.json
        source_path = data.get('source_path', '').strip()
        destination_path = data.get('destination_path', '').strip()
        item_type = data.get('item_type', 'file')

        if not source_path:
            return jsonify({'error': 'Source path is required'}), 400

        # Security: prevent directory traversal
        source_path = source_path.replace('..', '').strip('/')
        destination_path = destination_path.replace('..', '').strip('/')

        download_dir = Path(app.config['DOWNLOAD_FOLDER'])
        source_full = download_dir / source_path
        item_name = source_full.name

        # Build destination path
        if destination_path:
            dest_full = download_dir / destination_path / item_name
        else:
            dest_full = download_dir / item_name

        # Check if source exists
        if not source_full.exists():
            return jsonify({'error': 'Source does not exist'}), 404

        # Check if destination already exists
        if dest_full.exists():
            return jsonify({'error': f'An item with the name "{item_name}" already exists in the destination'}), 400

        # Move the item
        import shutil
        shutil.move(str(source_full), str(dest_full))
        app.logger.info(f"Moved {item_type}: {source_path} → {dest_full.relative_to(download_dir)}")

        return jsonify({'success': True, 'new_path': str(dest_full.relative_to(download_dir))})

    except Exception as e:
        app.logger.error(f"Error moving item: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/delete', methods=['DELETE'])
def delete_item():
    """Delete a file or folder"""
    try:
        data = request.json
        item_path = data.get('path', '').strip()
        item_type = data.get('item_type', 'file')

        if not item_path:
            return jsonify({'error': 'Path is required'}), 400

        # Security: prevent directory traversal
        item_path = item_path.replace('..', '').strip('/')

        download_dir = Path(app.config['DOWNLOAD_FOLDER'])
        full_path = download_dir / item_path

        # Check if item exists
        if not full_path.exists():
            return jsonify({'error': 'Item does not exist'}), 404

        # Delete the item with retry logic for Windows file locking
        import shutil
        import time
        import gc

        # Force garbage collection to release any file handles
        gc.collect()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if full_path.is_dir():
                    shutil.rmtree(full_path)
                    app.logger.info(f"Deleted folder: {item_path}")
                else:
                    full_path.unlink()
                    app.logger.info(f"Deleted file: {item_path}")
                return jsonify({'success': True})
            except PermissionError as pe:
                if attempt < max_retries - 1:
                    # Wait a bit and retry
                    app.logger.warning(f"File locked, retrying in 0.5s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(0.5)
                    gc.collect()  # Try to force cleanup again
                else:
                    # Final attempt failed
                    raise pe

    except PermissionError as pe:
        app.logger.error(f"Permission error deleting item (file may be in use): {pe}")
        return jsonify({'error': 'File is currently in use by another process. Please wait a moment and try again.'}), 423
    except Exception as e:
        app.logger.error(f"Error deleting item: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/filters', methods=['GET'])
def get_filters():
    """Get current hallucination filters from config.yaml"""
    import yaml

    config_path = 'config.yaml'
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                filters = config.get('hallucination_filters', {})

                # Return only the user-editable fields
                return jsonify({
                    'bad_phrases': filters.get('bad_phrases', []),
                    'bad_patterns': filters.get('bad_patterns', [])
                })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Return defaults if config doesn't exist
    return jsonify({
        'bad_phrases': [],
        'bad_patterns': []
    })


@app.route('/api/filters', methods=['POST'])
def save_filters():
    """Save hallucination filters to config.yaml"""
    import yaml

    data = request.get_json()
    config_path = 'config.yaml'

    try:
        # Load existing config
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

        # Update filter sections
        if 'hallucination_filters' not in config:
            config['hallucination_filters'] = {}

        config['hallucination_filters']['bad_phrases'] = data.get('bad_phrases', [])
        config['hallucination_filters']['bad_patterns'] = data.get('bad_patterns', [])

        # Save updated config
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return jsonify({'status': 'success', 'message': 'Filters saved successfully'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clean-subtitles', methods=['POST'])
def clean_subtitles_endpoint():
    """Clean existing subtitle file with hallucination filters"""
    import srt_cleanup
    import shutil
    from datetime import datetime

    data = request.get_json()
    file_path = data.get('file_path', '')

    if not file_path:
        return jsonify({'error': 'file_path is required'}), 400

    # Construct full path
    full_path = os.path.join(app.config['DOWNLOAD_FOLDER'], file_path)

    # Validate file exists
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404

    # Validate it's an SRT file
    if not full_path.endswith('.srt'):
        return jsonify({'error': 'File must be an SRT file'}), 400

    try:
        # Create backup before cleaning
        backup_path = full_path.replace('.srt', f'.srt.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        shutil.copy2(full_path, backup_path)

        # Load filters from config
        filters = srt_cleanup.load_custom_filters('config.yaml')

        # Load and clean subtitles
        segments = srt_cleanup.load_srt(full_path)

        clean_segments = []
        removed = 0
        shortened = 0

        for seg in segments:
            import copy
            seg_copy = copy.deepcopy(seg)
            result_seg, action, reason = srt_cleanup.clean_segment_text(seg_copy, filters)

            if action == 'kept':
                clean_segments.append(seg_copy)
            elif action == 'shortened':
                clean_segments.append(result_seg)
                shortened += 1
            elif action == 'removed':
                removed += 1

        # Save cleaned version (overwrite original)
        srt_cleanup.save_srt(clean_segments, full_path)

        # Prepare result message
        message = f"Shortened: {shortened}, Removed: {removed}, Kept: {len(clean_segments)}\nBackup: {os.path.basename(backup_path)}"

        return jsonify({
            'status': 'success',
            'message': message,
            'stats': {
                'shortened': shortened,
                'removed': removed,
                'kept': len(clean_segments),
                'backup_path': os.path.basename(backup_path)
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-subtitles', methods=['POST'])
def generate_subtitles_endpoint():
    """Generate subtitles for existing video file"""
    import uuid

    data = request.get_json()
    file_path = data.get('file_path', '')

    if not file_path:
        return jsonify({'error': 'file_path is required'}), 400

    # Construct full path
    full_path = os.path.join(app.config['DOWNLOAD_FOLDER'], file_path)

    # Validate file exists
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404

    # Validate it's a video file
    video_extensions = ['.mp4', '.mkv', '.avi', '.webm', '.mov']
    if not any(full_path.lower().endswith(ext) for ext in video_extensions):
        return jsonify({'error': 'File must be a video file'}), 400

    # Check if SRT already exists
    srt_path = os.path.splitext(full_path)[0] + '.srt'
    if os.path.exists(srt_path):
        return jsonify({'error': 'Subtitles already exist for this file'}), 400

    try:
        # Load config for default parameters
        import yaml
        config = {}
        if os.path.exists('config.yaml'):
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

        trans_config = config.get('transcription', {})

        # Create job parameters from config defaults
        parameters = {
            'model': trans_config.get('model', 'large-v3'),
            'device': trans_config.get('device', 'cuda'),
            'language': trans_config.get('language', 'sr'),
            'beam_size': trans_config.get('beam_size', 12),
            'workers': 1,
            'vad_filter': trans_config.get('vad_filter', False),
            'compute_type': trans_config.get('compute', 'float16'),
            'temperature': trans_config.get('temperature', 0.2),
            'source_type': 'upload',
            'auto_cleanup': False
        }

        # Create job ID
        job_id = str(uuid.uuid4())

        # Create pseudo-URL for the file
        url = f'file://{full_path}'

        # Save to database
        conn = get_db()
        now = datetime.now().isoformat()
        conn.execute('''INSERT INTO jobs (id, url, status, created_at, updated_at, parameters, job_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (job_id, url, 'queued', now, now, json.dumps(parameters), 'transcribe'))
        conn.commit()
        conn.close()

        # Emit socket event for immediate UI update
        try:
            socketio.emit('job_created', {
                'id': job_id,
                'url': url,
                'status': 'queued',
                'progress': 0,
                'created_at': now,
                'updated_at': now,
                'parameters': json.dumps(parameters),
                'job_type': 'transcribe',
                'parent_job_id': None,
                'result': None,
                'error': None
            })
            app.logger.debug(f"Emitted job_created event for generate-subtitles job {job_id}")
        except Exception as e:
            app.logger.warning(f"Failed to emit job creation event: {e}")

        # Start background job
        threading.Thread(target=run_transcription_job, args=(job_id, url, parameters), daemon=True).start()

        return jsonify({
            'status': 'success',
            'job_id': job_id,
            'message': 'Subtitle generation started'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
# Translation Endpoints
# ==========================================

# Language code to full name mapping
LANGUAGE_NAMES = {
    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
    'it': 'Italian', 'pt': 'Portuguese', 'pl': 'Polish', 'tr': 'Turkish',
    'ru': 'Russian', 'nl': 'Dutch', 'cs': 'Czech', 'ar': 'Arabic',
    'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean', 'hi': 'Hindi',
    'sv': 'Swedish', 'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish',
    'uk': 'Ukrainian', 'el': 'Greek', 'ro': 'Romanian', 'hu': 'Hungarian',
    'sr': 'Serbian', 'hr': 'Croatian', 'bg': 'Bulgarian', 'sk': 'Slovak',
    'sl': 'Slovenian', 'lt': 'Lithuanian', 'lv': 'Latvian', 'et': 'Estonian',
    'ga': 'Irish', 'vi': 'Vietnamese', 'th': 'Thai', 'id': 'Indonesian',
    'ms': 'Malay', 'he': 'Hebrew', 'fa': 'Persian', 'ca': 'Catalan',
}


@app.route('/api/translate', methods=['POST'])
def translate_text():
    """Translate text in real-time (for subtitle hints)"""
    if not TRANSLATOR_AVAILABLE:
        return jsonify({'error': 'Translation library not available'}), 503

    data = request.get_json()
    text = data.get('text', '')
    target_lang = data.get('target', 'en')
    source_lang = data.get('source', 'auto')

    if not text:
        return jsonify({'error': 'text is required'}), 400

    try:
        translator = Translator()
        result = translator.translate(text, src=source_lang, dest=target_lang)

        return jsonify({
            'status': 'success',
            'original': text,
            'translated': result.text,
            'source_lang': result.src,
            'target_lang': target_lang
        })

    except Exception as e:
        app.logger.error(f"Translation error: {e}")
        return jsonify({'error': f'Translation failed: {str(e)}'}), 500


@app.route('/api/transcode-to-mp4', methods=['POST'])
def transcode_to_mp4():
    """Transcode video file to MP4 format"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')

        if not file_path:
            return jsonify({'error': 'file_path is required'}), 400

        # Construct full path
        full_path = os.path.join(app.config['DOWNLOAD_FOLDER'], file_path)

        if not os.path.exists(full_path):
            return jsonify({'error': 'File not found'}), 404

        # Check if it's a video file
        video_extensions = ['.avi', '.mkv', '.webm', '.mov', '.flv', '.wmv', '.m4v']
        if not any(full_path.lower().endswith(ext) for ext in video_extensions):
            return jsonify({'error': 'File is not a transcodable video format'}), 400

        # Check if MP4 version already exists
        output_path = os.path.splitext(full_path)[0] + '.mp4'
        if os.path.exists(output_path):
            return jsonify({'error': 'MP4 version already exists'}), 400

        # Create job ID
        job_id = str(uuid.uuid4())

        # Create job parameters
        parameters = {
            'source_file': file_path,
            'output_file': os.path.basename(output_path),
            'job_type': 'transcode'
        }

        # Save to database
        conn = get_db()
        now = datetime.now().isoformat()
        url = f'transcode://{file_path}'
        conn.execute('''INSERT INTO jobs (id, url, status, created_at, updated_at, parameters, job_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (job_id, url, 'queued', now, now, json.dumps(parameters), 'transcode'))
        conn.commit()
        conn.close()

        # Emit socket event for immediate UI update
        try:
            socketio.emit('job_created', {
                'id': job_id,
                'url': url,
                'status': 'queued',
                'progress': 0,
                'created_at': now,
                'updated_at': now,
                'parameters': json.dumps(parameters),
                'job_type': 'transcode',
                'parent_job_id': None,
                'result': None,
                'error': None
            })
            app.logger.debug(f"Emitted job_created event for transcode job {job_id}")
        except Exception as e:
            app.logger.warning(f"Failed to emit job creation event: {e}")

        # Start transcoding job in background
        thread = threading.Thread(
            target=run_transcode_job,
            args=(job_id, full_path, output_path),
            daemon=True
        )
        thread.start()

        return jsonify({
            'status': 'success',
            'job_id': job_id,
            'message': f'Transcoding job started: {os.path.basename(file_path)} → MP4'
        })

    except Exception as e:
        app.logger.error(f"Transcode job error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/translate-subtitle', methods=['POST'])
def translate_subtitle():
    """Start a translation job for subtitle file"""
    if not TRANSLATOR_AVAILABLE:
        return jsonify({'error': 'Translation library not available'}), 503

    data = request.get_json()
    file_path = data.get('file_path', '')
    target_lang = data.get('target_lang', 'en')
    source_lang = data.get('source_lang', 'auto')

    if not file_path:
        return jsonify({'error': 'file_path is required'}), 400

    # Construct full path
    full_path = os.path.join(app.config['DOWNLOAD_FOLDER'], file_path)

    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404

    if not full_path.endswith('.srt'):
        return jsonify({'error': 'Only SRT files are supported'}), 400

    try:
        # Create job ID
        job_id = str(uuid.uuid4())

        # Create job parameters
        parameters = {
            'source_lang': source_lang,
            'target_lang': target_lang,
            'source_file': file_path,
            'job_type': 'translate'
        }

        # Save to database
        conn = get_db()
        now = datetime.now().isoformat()
        url = f'translate://{file_path}'
        conn.execute('''INSERT INTO jobs (id, url, status, created_at, updated_at, parameters, job_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (job_id, url, 'queued', now, now,
                      json.dumps(parameters), 'translate'))
        conn.commit()
        conn.close()

        # Emit socket event for immediate UI update
        try:
            socketio.emit('job_created', {
                'id': job_id,
                'url': url,
                'status': 'queued',
                'progress': 0,
                'created_at': now,
                'updated_at': now,
                'parameters': json.dumps(parameters),
                'job_type': 'translate',
                'parent_job_id': None,
                'result': None,
                'error': None
            })
            app.logger.debug(f"Emitted job_created event for translation job {job_id}")
        except Exception as e:
            app.logger.warning(f"Failed to emit job creation event: {e}")

        # Start translation job in background
        thread = threading.Thread(
            target=run_translation_job,
            args=(job_id, full_path, target_lang, source_lang),
            daemon=True
        )
        thread.start()

        return jsonify({
            'status': 'success',
            'job_id': job_id,
            'message': f'Translation job started: {source_lang} → {target_lang}'
        })

    except Exception as e:
        app.logger.error(f"Translation job error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload-temp', methods=['POST'])
def upload_temp():
    """Upload file to temporary location for stream detection"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Save file to temporary uploads folder
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{filename}')

        file.save(temp_path)

        return jsonify({
            'status': 'success',
            'temp_path': temp_path,
            'filename': filename
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect-audio-streams', methods=['POST'])
def detect_audio_streams():
    """Detect audio streams in uploaded file"""
    import subprocess
    import json as json_module

    data = request.get_json()
    temp_path = data.get('temp_path', '')

    if not temp_path or not os.path.exists(temp_path):
        return jsonify({'error': 'File not found'}), 400

    try:
        # Use ffprobe to detect audio streams
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=index,codec_name,channels,channel_layout,sample_rate:stream_tags=language,title',
            '-of', 'json',
            temp_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({'error': 'Failed to analyze file'}), 500

        data = json_module.loads(result.stdout)
        streams = data.get('streams', [])

        audio_tracks = []
        for i, stream in enumerate(streams):
            tags = stream.get('tags', {})
            track_info = {
                'index': stream.get('index', i),
                'codec': stream.get('codec_name', 'unknown'),
                'channels': stream.get('channels', 0),
                'sample_rate': stream.get('sample_rate', 0),
                'language': tags.get('language', 'und'),
                'title': tags.get('title', ''),
            }
            audio_tracks.append(track_info)

        return jsonify({'tracks': audio_tracks})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect-audio-streams-existing', methods=['POST'])
def detect_audio_streams_existing():
    """Detect audio streams in existing file"""
    import subprocess
    import json as json_module

    data = request.get_json()
    file_path = data.get('file_path', '')

    if not file_path:
        return jsonify({'error': 'File path is required'}), 400

    # Construct full path
    full_path = os.path.join(app.config['DOWNLOAD_FOLDER'], file_path)

    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404

    try:
        # Use ffprobe to detect audio streams
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=index,codec_name,channels,channel_layout,sample_rate:stream_tags=language,title',
            '-of', 'json',
            full_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({'error': 'Failed to analyze file'}), 500

        data = json_module.loads(result.stdout)
        streams = data.get('streams', [])

        audio_tracks = []
        for i, stream in enumerate(streams):
            tags = stream.get('tags', {})
            track_info = {
                'index': stream.get('index', i),
                'codec': stream.get('codec_name', 'unknown'),
                'channels': stream.get('channels', 0),
                'sample_rate': stream.get('sample_rate', 0),
                'language': tags.get('language', 'und'),
                'title': tags.get('title', ''),
            }
            audio_tracks.append(track_info)

        return jsonify({'tracks': audio_tracks})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload-file', methods=['POST'])
def upload_file():
    """Simple file upload without processing - supports target folder"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Get target folder from form data (optional)
    target_folder = request.form.get('target_folder', '').strip()

    try:
        # Validate filename
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'error': 'Invalid filename'}), 400

        # Validate file extension (only allow videos and subtitles)
        allowed_extensions = ['.mp4', '.mkv', '.avi', '.webm', '.mov', '.srt', '.vtt', '.ass']
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File type {file_ext} not allowed. Only video and subtitle files are permitted.'}), 400

        # Build target directory path
        if target_folder:
            # Security: prevent directory traversal
            target_folder = target_folder.replace('..', '').strip('/')
            target_dir = os.path.join(app.config['DOWNLOAD_FOLDER'], target_folder)
        else:
            target_dir = app.config['DOWNLOAD_FOLDER']

        # Create target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)

        # Build full file path
        file_path = os.path.join(target_dir, filename)

        # Check if file already exists
        if os.path.exists(file_path):
            # Add timestamp to make it unique
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{name}_{timestamp}{ext}"
            file_path = os.path.join(target_dir, filename)

        # Check available disk space (require at least 100MB free)
        import shutil
        stat = shutil.disk_usage(app.config['DOWNLOAD_FOLDER'])
        free_space_mb = stat.free / (1024 * 1024)
        if free_space_mb < 100:
            return jsonify({'error': f'Insufficient disk space (only {free_space_mb:.0f}MB available)'}), 507

        # Save file
        file.save(file_path)

        # Get relative path for response
        rel_path = os.path.relpath(file_path, app.config['DOWNLOAD_FOLDER']).replace('\\', '/')

        app.logger.info(f"File uploaded: {rel_path} ({os.path.getsize(file_path)} bytes)")

        return jsonify({
            'status': 'success',
            'filename': filename,
            'path': rel_path,
            'message': f'File uploaded: {filename}'
        })

    except PermissionError:
        app.logger.error(f"Permission denied when uploading file: {filename}")
        return jsonify({'error': 'Permission denied. Cannot write to upload directory.'}), 403
    except OSError as e:
        app.logger.error(f"OS error during upload: {e}")
        return jsonify({'error': f'File system error: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@app.route('/api/cookie-status', methods=['GET'])
def check_cookie_status():
    """Check if youtube_cookies.txt exists"""
    cookie_path = 'youtube_cookies.txt'

    if os.path.exists(cookie_path):
        file_size = os.path.getsize(cookie_path)
        # Format file size
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"

        # Get last modified time
        mtime = os.path.getmtime(cookie_path)
        modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

        return jsonify({
            'exists': True,
            'filename': 'youtube_cookies.txt',
            'size': size_str,
            'modified': modified
        })
    else:
        return jsonify({
            'exists': False
        })


@app.route('/api/jobs/clear', methods=['POST'])
def clear_jobs():
    """Clear completed and failed jobs from database"""
    data = request.get_json()
    statuses = data.get('statuses', ['completed', 'failed'])

    try:
        conn = get_db()
        placeholders = ','.join('?' for _ in statuses)
        query = f'DELETE FROM jobs WHERE status IN ({placeholders})'
        cursor = conn.execute(query, statuses)
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return jsonify({
            'status': 'success',
            'deleted': deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/<job_id>/restart', methods=['POST'])
def restart_job(job_id):
    """Restart a job with the same parameters"""
    import uuid

    try:
        # Get the original job
        conn = get_db()
        cursor = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
        job = cursor.fetchone()

        if not job:
            return jsonify({'error': 'Job not found'}), 404

        # Create new job ID
        new_job_id = str(uuid.uuid4())

        # Copy job data
        url = job[1]  # url column
        parameters = job[6]  # parameters column (index 6, not 5!)
        now = datetime.now().isoformat()

        # Debug: log parameters to see what we're working with
        app.logger.debug(f"Original parameters type: {type(parameters)}")
        app.logger.debug(f"Original parameters value: {repr(parameters)[:200]}")

        # Parse parameters to validate
        try:
            if isinstance(parameters, str):
                params = json.loads(parameters)
            elif isinstance(parameters, dict):
                params = parameters
            else:
                params = {}
        except json.JSONDecodeError as e:
            app.logger.error(f"Error parsing parameters: {e}")
            app.logger.error(f"Parameters content: {parameters[:500]}")
            return jsonify({'error': f'Invalid parameters format: {str(e)}', 'raw': str(parameters)[:200]}), 400

        # Ensure video_title is set (extract from URL if missing)
        if not params.get('video_title') or params.get('video_title') == 'Unknown Video':
            if url.startswith('file://'):
                # Extract filename from file:// URL
                file_path = url.replace('file://', '')
                video_title = os.path.splitext(os.path.basename(file_path))[0]
                # Remove YouTube ID pattern [xxx]
                video_title = re.sub(r'\s*\[[a-zA-Z0-9_-]{11}\]$', '', video_title)
                params['video_title'] = video_title.strip() or "Video"
                app.logger.info(f"Extracted video title: {params['video_title']}")

        # Convert back to string for storage
        parameters_str = json.dumps(params)

        # Get job type from original job
        job_type = job[9] if len(job) > 9 else 'transcribe'  # job_type column is index 9

        # Insert new job with correct job_type
        conn.execute('''INSERT INTO jobs (id, url, status, created_at, updated_at, parameters, job_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (new_job_id, url, 'queued', now, now, parameters_str, job_type))
        conn.commit()
        conn.close()

        # Emit socket event for immediate UI update
        try:
            socketio.emit('job_created', {
                'id': new_job_id,
                'url': url,
                'status': 'queued',
                'progress': 0,
                'created_at': now,
                'updated_at': now,
                'parameters': parameters_str,
                'job_type': job_type,
                'parent_job_id': None,
                'result': None,
                'error': None
            })
            app.logger.debug(f"Emitted job_created event for restarted job {new_job_id}")
        except Exception as e:
            app.logger.warning(f"Failed to emit job creation event: {e}")

        # Start background job with correct handler based on job type
        app.logger.info(f"Restarting job {job_id} as new job {new_job_id} with type '{job_type}'")

        if job_type == 'download':
            threading.Thread(target=run_download_job, args=(new_job_id, url, params), daemon=True).start()
        elif job_type == 'translate':
            # For translate jobs, we need to extract the srt_file_path
            srt_file = params.get('srt_file', '')
            target_lang = params.get('target_lang', 'en')
            source_lang = params.get('source_lang', 'auto')
            threading.Thread(target=run_translation_job, args=(new_job_id, srt_file, target_lang, source_lang), daemon=True).start()
        elif job_type == 'transcode':
            # For transcode jobs, extract input and output paths
            source_file = params.get('source_file', '')
            output_file = params.get('output_file', '')
            input_path = os.path.join(app.config['DOWNLOAD_FOLDER'], source_file)
            output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], os.path.dirname(source_file), output_file)
            threading.Thread(target=run_transcode_job, args=(new_job_id, input_path, output_path), daemon=True).start()
        else:  # transcribe
            threading.Thread(target=run_transcription_job, args=(new_job_id, url, params), daemon=True).start()

        return jsonify({
            'status': 'success',
            'new_job_id': new_job_id,
            'job_type': job_type,
            'message': f'Job restarted successfully as {job_type} job'
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        app.logger.error(f"Restart job error: {error_details}")
        return jsonify({'error': str(e), 'details': error_details}), 500


@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a running or queued job"""
    try:
        # Check if job exists and is in a cancellable state
        conn = get_db()
        cursor = conn.execute('SELECT status, url FROM jobs WHERE id = ?', (job_id,))
        job = cursor.fetchone()
        conn.close()

        if not job:
            return jsonify({'error': 'Job not found'}), 404

        status = job[0]
        url = job[1]

        if status not in ['queued', 'running']:
            return jsonify({'error': f'Cannot cancel job with status: {status}'}), 400

        # Kill associated ffmpeg process if it exists
        if job_id in active_job_processes:
            process = active_job_processes[job_id]
            try:
                app.logger.info(f"Killing ffmpeg process {process.pid} for job {job_id}")

                # Kill the process and all its children (Windows)
                try:
                    parent = psutil.Process(process.pid)
                    children = parent.children(recursive=True)

                    # Kill children first
                    for child in children:
                        try:
                            app.logger.info(f"Killing child process {child.pid}")
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass

                    # Then kill parent
                    parent.kill()
                    parent.wait(timeout=3)
                    app.logger.info(f"✓ Successfully killed process {process.pid}")
                except psutil.NoSuchProcess:
                    app.logger.warning(f"Process {process.pid} already terminated")
                except Exception as e:
                    app.logger.warning(f"Could not kill process {process.pid}: {e}")
                    # Fallback to simple terminate
                    process.terminate()

                # Remove from tracking dict
                active_job_processes.pop(job_id, None)
            except Exception as e:
                app.logger.error(f"Error killing process for job {job_id}: {e}")

        # Delete generated WAV file if it exists
        cleanup_wav_file(job_id)

        # Update job status to cancelled
        update_job_status(job_id, 'cancelled', 0)
        app.logger.info(f"Job {job_id} cancelled by user")

        return jsonify({'status': 'success', 'message': 'Job cancelled'})
    except Exception as e:
        app.logger.error(f"Error cancelling job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/<job_id>/delete', methods=['POST'])
def delete_job(job_id):
    """Delete a job from the database"""
    try:
        conn = get_db()
        cursor = conn.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted == 0:
            return jsonify({'error': 'Job not found'}), 404

        app.logger.info(f"Job {job_id} deleted by user")
        return jsonify({'status': 'success', 'message': 'Job deleted'})
    except Exception as e:
        app.logger.error(f"Error deleting job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/<job_id>/create-transcription', methods=['POST'])
def create_transcription_from_download(job_id):
    """Manually create transcription job(s) from a completed download job"""
    try:
        # Get the download job
        conn = get_db()
        job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
        conn.close()

        if not job:
            return jsonify({'error': 'Job not found'}), 404

        job_dict = dict(job)

        # Verify it's a download job
        if job_dict.get('job_type') != 'download':
            return jsonify({'error': 'This is not a download job'}), 400

        # Verify it's completed
        if job_dict.get('status') != 'completed':
            return jsonify({'error': 'Download job is not completed'}), 400

        # Parse parameters
        try:
            parameters = json.loads(job_dict['parameters'])
        except:
            parameters = {}

        # Scan download directory for video files
        download_dir = parameters.get('download_dir', 'yt_downloads')
        video_files = []

        app.logger.info(f"Scanning {download_dir} for video files...")

        for root, dirs, files in os.walk(download_dir):
            for file in files:
                if file.endswith(('.mp4', '.mkv', '.webm', '.avi', '.mov')):
                    file_path = os.path.join(root, file)
                    # Check if file was modified in last hour (recently downloaded)
                    import time
                    if time.time() - os.path.getmtime(file_path) < 3600:
                        video_files.append(file_path)
                        app.logger.info(f"Found recent video: {file_path}")

        if not video_files:
            return jsonify({'error': 'No video files found in download directory'}), 404

        # Create transcription jobs
        transcription_jobs = []
        for video_path in video_files:
            transcribe_job_id = create_transcription_job(job_id, video_path, parameters)
            if transcribe_job_id:
                transcription_jobs.append(transcribe_job_id)

        return jsonify({
            'status': 'success',
            'message': f'Created {len(transcription_jobs)} transcription job(s)',
            'job_ids': transcription_jobs
        })

    except Exception as e:
        app.logger.error(f"Error creating transcription jobs: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/system-info')
def get_system_info():
    """Get comprehensive system information including health metrics"""
    try:
        import platform
        import shutil

        # System Status
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        # Disk Usage
        disk = psutil.disk_usage('.')

        # Database Health
        db_path = 'whisper_jobs.db'
        db_health = {
            'exists': os.path.exists(db_path),
            'size': os.path.getsize(db_path) if os.path.exists(db_path) else 0,
            'size_mb': round(os.path.getsize(db_path) / (1024*1024), 2) if os.path.exists(db_path) else 0
        }

        # Try to count records
        try:
            conn = get_db()
            job_count = conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
            db_health['job_count'] = job_count
            conn.close()
            db_health['accessible'] = True
        except Exception as e:
            db_health['accessible'] = False
            db_health['error'] = str(e)

        # Directory Sizes
        directories = {
            'yt_downloads': 'yt_downloads',
            'uploads': 'uploads',
            'logs': 'logs',
            'backups': 'backups'
        }

        dir_sizes = {}
        for name, path in directories.items():
            if os.path.exists(path):
                total_size = 0
                file_count = 0
                for root, dirs, files in os.walk(path):
                    for file in files:
                        fp = os.path.join(root, file)
                        if os.path.exists(fp):
                            total_size += os.path.getsize(fp)
                            file_count += 1
                dir_sizes[name] = {
                    'size_bytes': total_size,
                    'size_mb': round(total_size / (1024*1024), 2),
                    'size_gb': round(total_size / (1024*1024*1024), 2),
                    'file_count': file_count,
                    'exists': True
                }
            else:
                dir_sizes[name] = {'exists': False, 'size_mb': 0, 'file_count': 0}

        # Process Information
        current_process = psutil.Process()
        process_info = {
            'pid': current_process.pid,
            'name': current_process.name(),
            'status': current_process.status(),
            'cpu_percent': current_process.cpu_percent(interval=0.1),
            'memory_mb': round(current_process.memory_info().rss / (1024*1024), 2),
            'memory_percent': round(current_process.memory_percent(), 2),
            'threads': current_process.num_threads(),
            'create_time': datetime.fromtimestamp(current_process.create_time()).isoformat()
        }

        # CUDA/GPU Information
        gpu_info = {'available': False}
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_devices = []
                for i in range(gpu_count):
                    props = torch.cuda.get_device_properties(i)
                    gpu_devices.append({
                        'id': i,
                        'name': props.name,
                        'total_memory_gb': round(props.total_memory / (1024**3), 2),
                        'capability': f"{props.major}.{props.minor}",
                        'multi_processor_count': props.multi_processor_count
                    })

                gpu_info = {
                    'available': True,
                    'count': gpu_count,
                    'devices': gpu_devices,
                    'cuda_version': torch.version.cuda,
                    'cudnn_version': torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None
                }
        except ImportError:
            gpu_info['message'] = 'PyTorch not installed'
        except Exception as e:
            gpu_info['error'] = str(e)

        # System Information
        system_info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'cpu_count_physical': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True)
        }

        return jsonify({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'system_status': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_used_gb': round(disk.used / (1024**3), 2)
            },
            'database': db_health,
            'directories': dir_sizes,
            'process': process_info,
            'gpu': gpu_info,
            'system': system_info
        })

    except Exception as e:
        app.logger.error(f"Error getting system info: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    app.logger.info(f"✓ WebSocket client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    app.logger.info(f"✗ WebSocket client disconnected: {request.sid}")


if __name__ == '__main__':
    import argparse
    import logging
    import sys

    # Suppress socket connection reset errors (happens when browser closes connection)
    class ConnectionResetFilter(logging.Filter):
        def filter(self, record):
            # Filter connection reset errors and broken pipe errors
            msg = str(record.msg) if hasattr(record, 'msg') else str(record)

            # Check exception info
            if hasattr(record, 'exc_info') and record.exc_info:
                exc_type = record.exc_info[0]
                if exc_type and exc_type.__name__ in ['ConnectionResetError', 'BrokenPipeError',
                                                       'ConnectionAbortedError', 'OSError']:
                    return False

            # Check message content
            if any(x in msg for x in [
                'ConnectionResetError',
                'WinError 10054',
                'WinError 10053',
                'BrokenPipeError',
                'forcibly closed',
                'Connection reset',
                'Broken pipe'
            ]):
                return False

            # Check if it's a traceback line
            if 'Traceback' in msg or 'File "' in msg:
                return False

            return True

    # Monkey-patch sys.excepthook to suppress connection errors in tracebacks
    import sys
    import io
    original_excepthook = sys.excepthook

    def silent_excepthook(exc_type, exc_value, exc_traceback):
        if exc_type in (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            return  # Silently ignore
        if exc_type == OSError and 'WinError 10054' in str(exc_value):
            return  # Silently ignore
        original_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = silent_excepthook

    # Wrap stderr to filter connection reset errors from eventlet tracebacks
    class FilteredStderr:
        def __init__(self, original_stderr):
            self.original_stderr = original_stderr
            self.buffer = []
            self.in_traceback = False
            self.traceback_buffer = []

        def write(self, text):
            # Buffer traceback lines to check if it's a connection error
            if 'Traceback (most recent call last):' in text:
                self.in_traceback = True
                self.traceback_buffer = [text]
                return

            if self.in_traceback:
                self.traceback_buffer.append(text)

                # Check if this is the error line (end of traceback)
                if any(err in text for err in ['Error:', 'Exception:']):
                    # Check if it's a connection error
                    traceback_text = ''.join(self.traceback_buffer)
                    if any(x in traceback_text for x in [
                        'ConnectionResetError',
                        'WinError 10054',
                        'WinError 10053',
                        'BrokenPipeError',
                        'forcibly closed'
                    ]):
                        # Drop the entire traceback
                        self.in_traceback = False
                        self.traceback_buffer = []
                        return
                    else:
                        # It's a real error, print the buffered traceback
                        for line in self.traceback_buffer:
                            self.original_stderr.write(line)
                        self.in_traceback = False
                        self.traceback_buffer = []
                        return
                return

            # Normal output
            self.original_stderr.write(text)

        def flush(self):
            self.original_stderr.flush()

        def __getattr__(self, name):
            return getattr(self.original_stderr, name)

    sys.stderr = FilteredStderr(sys.stderr)

    # Apply filter to multiple loggers
    for logger_name in ['werkzeug', 'eventlet.wsgi.server', 'eventlet.wsgi', 'eventlet', 'socketio', 'root']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)
        logger.addFilter(ConnectionResetFilter())
        for handler in logger.handlers:
            handler.addFilter(ConnectionResetFilter())

    # Also filter root logger and add handler
    logging.root.addFilter(ConnectionResetFilter())
    logging.root.setLevel(logging.ERROR)

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5555, help='Port to run on (default: 5555)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()

    # Check if debug mode should be enabled (default: True for development)
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    logger.info("")
    logger.info("🚀 Starting Whisper AI Transcriber Web Interface")
    logger.info(f"📡 Server running on http://localhost:{args.port}")
    logger.info(f"🌐 Access from network: http://<your-ip>:{args.port}")
    logger.info(f"📝 Logs: {log_file}")
    logger.info(f"🗄️  Database: jobs.db")
    logger.info(f"🔧 Debug mode: {debug_mode}")
    logger.info("")

    socketio.run(app, host=args.host, port=args.port, debug=debug_mode)
