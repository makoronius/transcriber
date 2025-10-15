"""
transcribe_single.py
──────────────────────────────────────────────
Downloads and transcribes a SINGLE YouTube video using yt-dlp and faster_whisper_latin.py

Unlike transcribe_playlist.py, this script:
  • Only processes the specific video ID provided
  • Tracks completion by YouTube video ID, not filename wildcards
  • Does NOT scan the entire download directory
  • Ideal for single video transcription from web UI

Usage:
  python transcribe_single.py "<video_url>"

Examples:
  python transcribe_single.py "https://www.youtube.com/watch?v=Ua8RUEcSRJ8"
  python transcribe_single.py "https://youtu.be/Ua8RUEcSRJ8"
"""

import os
import sys
import argparse
import subprocess
import datetime
import logging
import logging.handlers
import re
from pathlib import Path

# Dependency checks
try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("Error: yt-dlp is not installed.")
    print("Install it with: pip install yt-dlp")
    sys.exit(1)

try:
    import yaml
except ImportError:
    yaml = None

# Try to import transcribe_file for direct function calls
try:
    from faster_whisper_latin import transcribe_file
    TRANSCRIBE_AVAILABLE = True
except ImportError:
    TRANSCRIBE_AVAILABLE = False


def log(msg: str):
    """Print timestamped message to stdout and logger"""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    if logging.getLogger().hasHandlers():
        msg_lower = msg.lower()
        if "❌" in msg or "error" in msg_lower or "failed" in msg_lower:
            logging.error(msg)
        elif "⚠️" in msg or "warning" in msg_lower:
            logging.warning(msg)
        else:
            logging.info(msg)


def load_config():
    """Load config.yaml if available"""
    if yaml and os.path.exists("config.yaml"):
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            log(f"⚠️  Could not load config.yaml: {e}")
    return {}


def setup_logging(config):
    """Setup file logging based on config"""
    log_config = config.get("logging", {})
    if not log_config.get("enabled", True):
        return

    log_file = log_config.get("log_file", "logs/transcribe.log")
    log_level = getattr(logging, log_config.get("log_level", "INFO").upper(), logging.INFO)
    max_size = log_config.get("max_size_mb", 10) * 1024 * 1024
    backup_count = log_config.get("backup_count", 3)

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_size, backupCount=backup_count, encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(handler)


def extract_video_id(url):
    """Extract YouTube video ID from various URL formats"""
    # Match patterns like:
    # - https://www.youtube.com/watch?v=VIDEO_ID
    # - https://youtu.be/VIDEO_ID
    # - https://www.youtube.com/watch?v=VIDEO_ID&list=...
    patterns = [
        r'(?:v=|/)([0-9A-Za-z_-]{11})(?:[&?]|$)',
        r'youtu\.be/([0-9A-Za-z_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_video_transcribed(video_id, download_dir):
    """Check if video has already been transcribed by checking for .srt file"""
    # Search for any .srt file containing the video ID in its name
    for root, dirs, files in os.walk(download_dir):
        for file in files:
            if file.endswith('.srt') and video_id in file:
                srt_path = os.path.join(root, file)
                log(f"✅ Video {video_id} already transcribed: {file}")
                return True, srt_path
    return False, None


def get_video_file(video_id, download_dir):
    """Find the video file for a given video ID"""
    for root, dirs, files in os.walk(download_dir):
        for file in files:
            if file.endswith('.mp4') and video_id in file:
                return os.path.join(root, file)
    return None


def download_video(url, video_id, download_dir, cookie_file=None):
    """Download a single video using yt-dlp"""
    log(f"📥 Downloading video: {video_id}")

    outtmpl = os.path.join(download_dir, "%(title)s [%(id)s].%(ext)s")

    ytdlp_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "concurrent_fragment_downloads": 10,
        "quiet": False,
        "no_warnings": False,
    }

    if cookie_file and os.path.exists(cookie_file):
        ytdlp_opts["cookiefile"] = cookie_file
        log(f"🍪 Using cookies: {cookie_file}")

    try:
        with YoutubeDL(ytdlp_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                # Get the downloaded file path
                video_file = get_video_file(video_id, download_dir)
                if video_file:
                    log(f"✅ Download complete: {os.path.basename(video_file)}")
                    return video_file
                else:
                    log(f"⚠️  Video downloaded but file not found")
                    return None
    except Exception as e:
        log(f"❌ Download failed: {e}")
        return None


def transcribe_video(video_path, transcriber, transcriber_args=None):
    """Transcribe a video file using the specified transcriber script (subprocess fallback)"""
    if not os.path.exists(video_path):
        log(f"❌ Video file not found: {video_path}")
        return False

    if not os.path.exists(transcriber):
        log(f"❌ Transcriber script not found: {transcriber}")
        return False

    log(f"🎙️  Starting transcription: {os.path.basename(video_path)}")

    # Build command
    cmd = [sys.executable, transcriber, video_path]
    if transcriber_args:
        cmd.extend(transcriber_args)

    log(f"   Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=False,  # Let output go to stdout/stderr directly
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            srt_path = os.path.splitext(video_path)[0] + ".srt"
            if os.path.exists(srt_path):
                log(f"✅ Transcription complete: {os.path.basename(srt_path)}")
                return True
            else:
                log(f"⚠️  Transcription finished but .srt file not found")
                return False
        else:
            log(f"❌ Transcription failed with exit code: {result.returncode}")
            return False
    except Exception as e:
        log(f"❌ Transcription error: {e}")
        return False


def transcribe_single_video(
    video_url,
    download_dir="yt_downloads",
    cookie_file=None,
    force=False,
    transcription_params=None,
    progress_callback=None
):
    """
    Download and transcribe a single YouTube video.

    This is the main importable function that can be called from other modules
    like web_app.py. It uses direct function calls instead of subprocess.

    Args:
        video_url: YouTube video URL
        download_dir: Directory to download videos to
        cookie_file: Optional cookie file for yt-dlp authentication
        force: Force re-transcription even if .srt exists
        transcription_params: Dict of transcription parameters:
            - model: Model name (default: "large-v3")
            - device: Device to use (default: "cuda")
            - compute_type: Compute type (default: "float16")
            - language: Language code (default: "sr")
            - beam_size: Beam size (default: 12)
            - vad_filter: VAD filter (default: False)
            - temperature: Temperature (default: 0.2)
            And other parameters from faster_whisper_latin
        progress_callback: Optional callback function(percent, message) for progress updates

    Returns:
        dict: {
            'video_id': str,
            'video_path': str,
            'srt_path': str,
            'video_title': str
        }

    Raises:
        ValueError: If video ID cannot be extracted from URL
        RuntimeError: If download or transcription fails
    """
    def report_progress(percent, message):
        """Helper to report progress"""
        if progress_callback:
            progress_callback(percent, message)
        else:
            log(message)

    # Default transcription parameters
    trans_params = transcription_params or {}

    # Create download directory
    os.makedirs(download_dir, exist_ok=True)

    report_progress(0, "🔍 Extracting video ID...")

    # Extract video ID
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {video_url}")

    report_progress(5, f"📹 Video ID: {video_id}")

    # Check if already transcribed
    if not force:
        is_done, srt_path = is_video_transcribed(video_id, download_dir)
        if is_done:
            # Get video file
            video_file = get_video_file(video_id, download_dir)
            if video_file:
                report_progress(100, f"✅ Video already transcribed")
                return {
                    'video_id': video_id,
                    'video_path': video_file,
                    'srt_path': srt_path,
                    'video_title': os.path.basename(video_file)
                }

    # Check if video file exists
    video_file = get_video_file(video_id, download_dir)
    video_title = None

    if not video_file:
        # Download the video
        report_progress(10, f"📥 Downloading video: {video_id}")

        outtmpl = os.path.join(download_dir, "%(title)s [%(id)s].%(ext)s")

        ytdlp_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
            "merge_output_format": "mp4",
            "outtmpl": outtmpl,
            "concurrent_fragment_downloads": 10,
            "quiet": True,
            "no_warnings": True,
        }

        if cookie_file and os.path.exists(cookie_file):
            ytdlp_opts["cookiefile"] = cookie_file
            report_progress(12, f"🍪 Using cookies: {cookie_file}")

        # Add progress hook
        def download_progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    if 'downloaded_bytes' in d and 'total_bytes' in d:
                        percent = (d['downloaded_bytes'] / d['total_bytes']) * 30  # Map to 10-40%
                        report_progress(10 + int(percent), f"📥 Downloading: {10 + percent:.1f}%")
                    elif '_percent_str' in d:
                        percent_str = d['_percent_str'].strip().replace('%', '')
                        percent = float(percent_str) * 0.3  # Map to 10-40%
                        report_progress(10 + int(percent), f"📥 Downloading: {percent_str}")
                except:
                    pass
            elif d['status'] == 'finished':
                report_progress(40, "✅ Download complete")

        ytdlp_opts['progress_hooks'] = [download_progress_hook]

        try:
            with YoutubeDL(ytdlp_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                if info:
                    video_title = info.get('title', 'Unknown')
                    # Get the downloaded file path
                    video_file = get_video_file(video_id, download_dir)
                    if not video_file:
                        raise RuntimeError("Video downloaded but file not found")
                    report_progress(40, f"✅ Downloaded: {os.path.basename(video_file)}")
                else:
                    raise RuntimeError("Failed to extract video info")
        except Exception as e:
            raise RuntimeError(f"Download failed: {e}")
    else:
        report_progress(40, f"✅ Video already downloaded: {os.path.basename(video_file)}")
        video_title = os.path.basename(video_file)

    # Transcribe the video
    report_progress(45, f"🎙️ Starting transcription...")

    if TRANSCRIBE_AVAILABLE:
        # Use direct function call (preferred method)
        def transcribe_progress_callback(percent, message):
            # Map transcription progress from 45% to 100%
            mapped_percent = 45 + int(percent * 0.55)
            report_progress(mapped_percent, f"🎙️ {message}")

        try:
            srt_path, segment_count = transcribe_file(
                input_path=video_file,
                output_path=None,  # Will auto-generate with language suffix
                model_name=trans_params.get('model', 'large-v3'),
                device=trans_params.get('device', 'cuda'),
                compute_type=trans_params.get('compute_type', 'float16'),
                language=trans_params.get('language', 'sr'),
                beam_size=trans_params.get('beam_size', 12),
                vad_filter=trans_params.get('vad_filter', False),
                temperature=trans_params.get('temperature', 0.2),
                no_speech_threshold=trans_params.get('no_speech_threshold', 0.1),
                compression_threshold=trans_params.get('compression_threshold', 2.8),
                chunk_length=trans_params.get('chunk_length', None),
                progress_callback=transcribe_progress_callback
            )

            report_progress(100, f"✅ Transcription complete! {segment_count} segments")

            return {
                'video_id': video_id,
                'video_path': video_file,
                'srt_path': srt_path,
                'video_title': video_title or os.path.basename(video_file)
            }

        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}")
    else:
        # Fallback to subprocess (legacy method)
        report_progress(50, "🎙️ Using subprocess transcription (fallback)...")

        transcriber = "faster_whisper_latin.py"
        if not os.path.exists(transcriber):
            raise RuntimeError(f"Transcriber script not found: {transcriber}")

        success = transcribe_video(video_file, transcriber, None)

        if success:
            # Find the generated SRT file
            base_name = os.path.splitext(video_file)[0]
            # Try language-suffixed version first
            lang = trans_params.get('language', 'sr')
            srt_path = f"{base_name}.{lang}.srt"
            if not os.path.exists(srt_path):
                # Try legacy version
                srt_path = f"{base_name}.srt"

            if os.path.exists(srt_path):
                report_progress(100, f"✅ Transcription complete")
                return {
                    'video_id': video_id,
                    'video_path': video_file,
                    'srt_path': srt_path,
                    'video_title': video_title or os.path.basename(video_file)
                }
            else:
                raise RuntimeError("Transcription finished but .srt file not found")
        else:
            raise RuntimeError("Transcription subprocess failed")


def main():
    log("=" * 60)
    log("Single Video Transcription Started")
    log("=" * 60)

    # Load configuration
    config = load_config()
    dl_config = config.get("download", {})
    trans_config = config.get("transcription", {})

    # Setup logging
    setup_logging(config)

    # Parse arguments
    parser = argparse.ArgumentParser(description="Download and transcribe a single YouTube video.")
    parser.add_argument("video_url", help="YouTube video URL")
    parser.add_argument("--download-dir", default=dl_config.get("download_dir", "yt_downloads"),
                       help="Download directory")
    parser.add_argument("--transcriber", default=trans_config.get("transcriber", "faster_whisper_latin.py"),
                       help="Path to transcription script")
    parser.add_argument("--cookies", default=dl_config.get("cookies", "youtube_cookies.txt"),
                       help="Cookie file for yt-dlp")
    parser.add_argument("--force", action="store_true",
                       help="Force re-transcription even if .srt exists")
    parser.add_argument("--transcriber-args", nargs=argparse.REMAINDER,
                       help="Arguments passed to transcriber")
    args = parser.parse_args()

    os.makedirs(args.download_dir, exist_ok=True)

    # Extract video ID
    video_id = extract_video_id(args.video_url)
    if not video_id:
        log(f"❌ Could not extract video ID from URL: {args.video_url}")
        return 1

    log(f"📹 Video ID: {video_id}")
    log(f"🔗 URL: {args.video_url}")

    # Check if already transcribed
    if not args.force:
        is_done, srt_path = is_video_transcribed(video_id, args.download_dir)
        if is_done:
            log(f"✅ Video already transcribed. Use --force to re-transcribe.")
            log(f"   SRT: {srt_path}")
            return 0

    # Check if video file exists
    video_file = get_video_file(video_id, args.download_dir)

    if not video_file:
        # Download the video
        video_file = download_video(args.video_url, video_id, args.download_dir, args.cookies)
        if not video_file:
            log(f"❌ Failed to download video")
            return 1
    else:
        log(f"✅ Video already downloaded: {os.path.basename(video_file)}")

    # Transcribe the video
    success = transcribe_video(video_file, args.transcriber, args.transcriber_args)

    if success:
        log("=" * 60)
        log("✅ Single Video Transcription Complete!")
        log("=" * 60)
        return 0
    else:
        log("=" * 60)
        log("❌ Transcription Failed")
        log("=" * 60)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        log(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
