"""
transcribe_playlist.py
──────────────────────────────────────────────
Downloads a YouTube playlist using yt-dlp and transcribes each video
with faster_whisper_latin.py immediately after it's available.

Features:
  • Live queue: each completed .mp4 is transcribed immediately
  • Pre-scan: already-downloaded videos missing .srt are queued first
  • Skip .srt or .mp4 intelligently (no duplication)
  • Full timestamped logging
  • Cookie file auto-detection and validation
  • Parallel transcription with configurable workers

Usage:
  python transcribe_playlist.py "<playlist_url>"

Examples:
  python transcribe_playlist.py "https://youtube.com/playlist?list=XXXX"
  python transcribe_playlist.py "..." --workers 3
"""

import os
import sys
import argparse
import queue
import threading
import subprocess
import datetime
import logging
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor, as_completed

# Dependency checks with helpful error messages
try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("Error: yt-dlp is not installed.")
    print("Install it with: pip install yt-dlp")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not installed
    tqdm = None

try:
    import yaml
except ImportError:
    yaml = None

# Try to import transcribe_file for direct function calls
try:
    from faster_whisper_latin import transcribe_file as transcribe_file_direct
    TRANSCRIBE_AVAILABLE = True
except ImportError:
    TRANSCRIBE_AVAILABLE = False


# ------------------------------------------------------------
# Utility: timestamped log output
# ------------------------------------------------------------
def log(msg: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    # Also write to file logger if configured
    if logging.getLogger().hasHandlers():
        # Determine log level based on message content
        msg_lower = msg.lower()
        if "❌" in msg or "error" in msg_lower or "failed" in msg_lower:
            logging.error(msg)
        elif "⚠️" in msg or "warning" in msg_lower:
            logging.warning(msg)
        else:
            logging.info(msg)


# ------------------------------------------------------------
# Utility: guess final output path from yt-dlp info
# ------------------------------------------------------------
def guess_output_path(info_dict, base_outtmpl, output_dir):
    if not info_dict:
        return None
    fp = info_dict.get("filepath") or info_dict.get("_filename")
    if fp and os.path.exists(fp):
        return fp
    # fallback — find latest .mp4 in output_dir
    latest = None
    latest_time = 0
    for root, _, files in os.walk(output_dir):
        for f in files:
            if f.lower().endswith(".mp4"):
                full = os.path.join(root, f)
                t = os.path.getmtime(full)
                if t > latest_time:
                    latest, latest_time = full, t
    return latest


# ------------------------------------------------------------
# Utility: cookie validation
# ------------------------------------------------------------
def show_cookie_status(cookie_path):
    if not os.path.exists(cookie_path):
        log(f"⚠️  Cookie file not found: {cookie_path}")
        return False
    size = os.path.getsize(cookie_path)
    with open(cookie_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = sum(1 for _ in f)
    log(f"🍪 Cookies file loaded: {cookie_path}")
    log(f"   Lines: {lines:,} | Size: {size/1024:.1f} KB")
    if lines < 10 or size < 512:
        log("⚠️  Warning: Cookie file seems too small — login may be incomplete.")
        return False
    else:
        log("✅  Cookies appear valid and will be used by yt-dlp.")
        return True


# ------------------------------------------------------------
# Configuration loading
# ------------------------------------------------------------
def load_config(config_path: str = "config.yaml"):
    """Load configuration from YAML file if it exists."""
    if yaml is None:
        return {}

    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            log(f"📝 Loaded configuration from {config_path}")
            return config or {}
    except Exception as e:
        log(f"⚠️  Warning: Failed to load config file: {e}")
        return {}


def setup_logging(config: dict):
    """Setup file logging with rotation based on config."""
    log_config = config.get("logging", {})

    if not log_config.get("enabled", True):
        return

    log_file = log_config.get("log_file", "transcribe.log")
    log_level = log_config.get("log_level", "INFO")
    max_size = log_config.get("max_size_mb", 10) * 1024 * 1024  # Convert MB to bytes
    backup_count = log_config.get("backup_count", 3)

    # Create rotating file handler with UTF-8 encoding
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size if max_size > 0 else 0,
        backupCount=backup_count,
        encoding='utf-8'  # Force UTF-8 encoding to handle Unicode characters
    )

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    logger.addHandler(handler)

    logging.info("="*60)
    logging.info("Playlist transcription session started")


# ------------------------------------------------------------
# Transcription with retry logic
# ------------------------------------------------------------
def transcribe_file_subprocess(path, transcriber, extra_args, index, total, max_retries=2):
    """Transcribe using subprocess (fallback method)"""
    srt_path = os.path.splitext(path)[0] + ".srt"
    if os.path.exists(srt_path):
        log(f"⏭️  [{index}/{total}] SRT exists, skipping: {os.path.basename(srt_path)}")
        return

    log(f"🎙️  [{index}/{total}] Starting transcription: {os.path.basename(path)}")
    cmd = [sys.executable, transcriber, path] + (extra_args or [])

    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            log(f"✅  [{index}/{total}] Done: {os.path.basename(path)}")
            return
        except subprocess.CalledProcessError as e:
            if attempt < max_retries:
                log(f"⚠️  [{index}/{total}] Attempt {attempt+1} failed, retrying... ({os.path.basename(path)})")
            else:
                log(f"❌  [{index}/{total}] Failed after {max_retries+1} attempts: {os.path.basename(path)}")
                log(f"   Error: {e.stderr if e.stderr else str(e)}")
        except FileNotFoundError:
            log(f"❌  [{index}/{total}] Transcriber script not found: {transcriber}")
            log(f"   Make sure '{transcriber}' exists in the current directory")
            return
        except Exception as e:
            log(f"❌  [{index}/{total}] Unexpected error: {os.path.basename(path)} - {str(e)}")
            return


def transcribe_file(path, transcription_params, index, total, max_retries=2, progress_callback=None):
    """
    Transcribe a file using direct function call or subprocess fallback.

    Args:
        path: Path to video file
        transcription_params: Dict of transcription parameters (model, device, language, etc.)
        index: Current file index (for logging)
        total: Total files (for logging)
        max_retries: Number of retry attempts
        progress_callback: Optional callback(percent, message) for progress updates
    """
    # Check for language-suffixed SRT files
    base_name = os.path.splitext(path)[0]
    lang = transcription_params.get('language', 'sr')
    srt_path = f"{base_name}.{lang}.srt"

    # Also check legacy SRT without suffix
    legacy_srt = f"{base_name}.srt"
    if os.path.exists(srt_path) or os.path.exists(legacy_srt):
        log(f"⏭️  [{index}/{total}] SRT exists, skipping: {os.path.basename(path)}")
        return

    log(f"🎙️  [{index}/{total}] Starting transcription: {os.path.basename(path)}")

    if TRANSCRIBE_AVAILABLE:
        # Use direct function call (preferred method)
        for attempt in range(max_retries + 1):
            try:
                def local_progress_callback(percent, message):
                    """Local progress callback for this file"""
                    log(f"    [{index}/{total}] {message}")
                    if progress_callback:
                        progress_callback(index, total, percent, message)

                output_path, segment_count = transcribe_file_direct(
                    input_path=path,
                    output_path=None,  # Will auto-generate with language suffix
                    model_name=transcription_params.get('model', 'large-v3'),
                    device=transcription_params.get('device', 'cuda'),
                    compute_type=transcription_params.get('compute_type', 'float16'),
                    language=lang,
                    beam_size=transcription_params.get('beam_size', 12),
                    vad_filter=transcription_params.get('vad_filter', False),
                    temperature=transcription_params.get('temperature', 0.2),
                    no_speech_threshold=transcription_params.get('no_speech_threshold', 0.1),
                    compression_threshold=transcription_params.get('compression_threshold', 2.8),
                    chunk_length=transcription_params.get('chunk_length', None),
                    progress_callback=local_progress_callback
                )

                log(f"✅  [{index}/{total}] Done: {os.path.basename(path)} ({segment_count} segments)")
                return

            except Exception as e:
                if attempt < max_retries:
                    log(f"⚠️  [{index}/{total}] Attempt {attempt+1} failed, retrying... ({os.path.basename(path)})")
                    log(f"   Error: {str(e)}")
                else:
                    log(f"❌  [{index}/{total}] Failed after {max_retries+1} attempts: {os.path.basename(path)}")
                    log(f"   Error: {str(e)}")
    else:
        # Fallback to subprocess
        log(f"   Using subprocess fallback (transcribe_file module not available)")
        transcriber = transcription_params.get('transcriber', 'faster_whisper_latin.py')
        extra_args = transcription_params.get('extra_args', None)
        transcribe_file_subprocess(path, transcriber, extra_args, index, total, max_retries)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    # Load configuration file
    config = load_config()
    dl_config = config.get("download", {})
    trans_config = config.get("transcription", {})

    # Setup logging
    setup_logging(config)

    parser = argparse.ArgumentParser(description="Download YouTube playlist and transcribe videos in real time.")
    parser.add_argument("playlist_url", help="YouTube playlist URL")
    parser.add_argument("--download-dir", default=dl_config.get("download_dir", "yt_downloads"),
                       help="Base folder for downloads")
    parser.add_argument("--transcriber", default=trans_config.get("transcriber", "faster_whisper_latin.py"),
                       help="Path to transcription script")
    parser.add_argument("--workers", type=int, default=dl_config.get("workers", 1),
                       help="Parallel transcription workers")
    parser.add_argument("--cookies", default=dl_config.get("cookies", "youtube_cookies.txt"),
                       help="Cookie file or browser[:profile]")
    parser.add_argument("--skip-existing-srt", action="store_true",
                       default=dl_config.get("skip_existing_srt", True),
                       help="Skip transcription if .srt already exists")
    parser.add_argument("--skip-existing-video", action="store_true",
                       default=dl_config.get("skip_existing_video", True),
                       help="Skip download if video already exists (uses downloaded.txt)")
    parser.add_argument("--transcriber-args", nargs=argparse.REMAINDER, help="Arguments passed to transcriber")
    args = parser.parse_args()

    os.makedirs(args.download_dir, exist_ok=True)
    completed_q = queue.Queue()
    stop_flag = object()

    # --------------------------------------------------------
    # Progress hook: enqueue after successful download
    # --------------------------------------------------------
    def progress_hook(d):
        if d.get("status") == "finished":
            info = d.get("info_dict") or {}
            path = guess_output_path(info, outtmpl, args.download_dir)
            if path and os.path.exists(path):
                log(f"⬇️  Download finished: {os.path.basename(path)} → queued for transcription")
                completed_q.put(path)

    # --------------------------------------------------------
    # yt-dlp config
    # --------------------------------------------------------
    fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4"
    outtmpl = os.path.join(args.download_dir, "%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s")

    ytdlp_opts = {
        "format": fmt,
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "concurrent_fragment_downloads": 10,
        "ignoreerrors": True,
        "quiet": False,
        "progress_hooks": [progress_hook],
        "download_archive": os.path.join(args.download_dir, "downloaded.txt"),
    }

    # --------------------------------------------------------
    # Cookie handling
    # --------------------------------------------------------
    cookie_used = False
    if args.cookies:
        if os.path.isfile(args.cookies):
            ytdlp_opts["cookiefile"] = args.cookies
            cookie_used = show_cookie_status(args.cookies)
        else:
            log(f"⚠️  Cookie file not found: {args.cookies}")
    elif os.path.exists("youtube_cookies.txt"):
        ytdlp_opts["cookiefile"] = "youtube_cookies.txt"
        cookie_used = show_cookie_status("youtube_cookies.txt")

    # --------------------------------------------------------
    # Pre-scan Phase 0: already downloaded files in archive
    # --------------------------------------------------------
    archive_path = ytdlp_opts["download_archive"]
    if os.path.exists(archive_path):
        log("🔍 Checking download archive for already-downloaded videos...")
        with open(archive_path, "r", encoding="utf-8", errors="ignore") as f:
            downloaded_ids = {line.strip() for line in f if line.strip()}
        for root, _, files in os.walk(args.download_dir):
            for fn in files:
                if fn.lower().endswith(".mp4"):
                    log(f"{fn} file checking")
                    full = os.path.join(root, fn)
                    srt = os.path.splitext(full)[0] + ".srt"
                    if not os.path.exists(srt):
                        log(f"📄 Archived video found (missing SRT): {fn}")
                        completed_q.put(full)
    else:
        log("ℹ️ No download archive found — all videos will be downloaded fresh.")

    # --------------------------------------------------------
    # Build transcription parameters from config and args
    # --------------------------------------------------------
    transcription_params = {
        'model': trans_config.get('model', 'large-v3'),
        'device': trans_config.get('device', 'cuda'),
        'compute_type': trans_config.get('compute_type', 'float16'),
        'language': trans_config.get('language', 'sr'),
        'beam_size': trans_config.get('beam_size', 12),
        'vad_filter': trans_config.get('vad_filter', False),
        'temperature': trans_config.get('temperature', 0.2),
        'no_speech_threshold': trans_config.get('no_speech_threshold', 0.1),
        'compression_threshold': trans_config.get('compression_threshold', 2.8),
        'chunk_length': trans_config.get('chunk_length', None),
        'transcriber': args.transcriber,  # For subprocess fallback
        'extra_args': args.transcriber_args,  # For subprocess fallback
    }

    # --------------------------------------------------------
    # Consumer (transcription queue)
    # --------------------------------------------------------
    def consumer():
        log(f"🚀 Transcription queue active with {args.workers} worker(s). Waiting for files...")
        index = 1
        total = 999
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = []
            while True:
                item = completed_q.get()
                if item is stop_flag:
                    break
                srt_path = os.path.splitext(item)[0] + ".srt"
                if args.skip_existing_srt and os.path.exists(srt_path):
                    log(f"⏭️  Skipping (SRT exists): {os.path.basename(item)}")
                    continue
                max_retries = trans_config.get("max_retries", 2)
                futures.append(pool.submit(transcribe_file, item, transcription_params, index, total, max_retries, None))
                index += 1

            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    log(f"❌ Worker crashed: {e}")

    log("🧵 Starting transcription queue...")
    consumer_thread = threading.Thread(target=consumer, daemon=True)
    consumer_thread.start()

    # --------------------------------------------------------
    # yt-dlp run
    # --------------------------------------------------------
    log("──────────────────────────────────────────────")
    log(f"▶️  Starting playlist: {args.playlist_url}")
    log(f"   Cookies: {'✅ yes' if cookie_used else '❌ none'}")
    log(f"   Skip existing video: {args.skip_existing_video}")
    log(f"   Skip existing SRT:   {args.skip_existing_srt}")
    log(f"   Workers: {args.workers}")
    log("──────────────────────────────────────────────")

    try:
        with YoutubeDL(ytdlp_opts) as ydl:
            ydl.download([args.playlist_url])
    except Exception as e:
        log(f"❌ Error during download: {e}")
        error_msg = str(e).lower()
        if "403" in error_msg or "429" in error_msg:
            log("   This may be due to:")
            log("   - Rate limiting (wait a few minutes)")
            log("   - Missing/invalid cookies (use --cookies)")
            log("   - Region-restricted content")
        elif "sign in" in error_msg or "private" in error_msg:
            log("   This playlist requires authentication.")
            log("   Export cookies from your browser and use --cookies youtube_cookies.txt")
        elif "not found" in error_msg or "unavailable" in error_msg:
            log("   Check that the playlist URL is correct and publicly accessible")
        log("   Some videos may have been downloaded before the error occurred.")

    # --------------------------------------------------------
    # Stop queue and finish
    # --------------------------------------------------------
    completed_q.put(stop_flag)
    consumer_thread.join()
    log("✅ All downloads and transcriptions completed.")


if __name__ == "__main__":
    main()
