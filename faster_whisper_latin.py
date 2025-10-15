"""
faster_whisper_latin.py
-----------------------
Transcribes audio or video using faster-whisper on GPU (CUDA),
automatically transliterates Serbian Cyrillic → Latin,
denoises, normalizes, and filters out hallucinated subtitles.

Features:
    • Automatic FFmpeg preprocessing for noisy audio (RNNoise + Loudnorm)
    • Adaptive decoding for low-volume or distorted speech
    • Robust hallucination filtering (uh, mmm, filler text, etc.)
    • Safe for batch and single use
    • Outputs .srt subtitles in Latin alphabet

Usage:
    python faster_whisper_latin.py <input_file> [--model MODEL_NAME]

Examples:
    python faster_whisper_latin.py "movie.mp4" --vad True --beam 15 --temp 0.3
"""

import sys
import os
import re
import argparse
import subprocess
import shutil
import logging
from logging.handlers import RotatingFileHandler

# Fix Windows console encoding to handle emojis and UTF-8 characters
if sys.platform == 'win32':
    try:
        # Reconfigure stdout to use UTF-8 encoding
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # If reconfiguration fails, continue anyway

# Dependency checks with helpful error messages
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("❌ Error: faster-whisper is not installed.")
    print("   Install it with: pip install faster-whisper")
    print("   For GPU support, also install: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
    sys.exit(1)

try:
    from transliterate import translit
except ImportError:
    print("❌ Error: transliterate is not installed.")
    print("   Install it with: pip install transliterate")
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


# -----------------------------
# Language Code Mapping
# -----------------------------
# Maps Whisper language codes to 2-letter ISO codes for file suffixes
LANGUAGE_SUFFIX_MAP = {
    # 2-letter and 3-letter ISO 639 codes
    'en': 'en',   # English
    'eng': 'en',  # English (3-letter)
    'es': 'es',   # Spanish
    'spa': 'es',  # Spanish (3-letter)
    'fr': 'fr',   # French
    'fra': 'fr',  # French (3-letter)
    'fre': 'fr',  # French (3-letter alternative)
    'de': 'de',   # German
    'deu': 'de',  # German (3-letter)
    'ger': 'de',  # German (3-letter alternative)
    'it': 'it',   # Italian
    'ita': 'it',  # Italian (3-letter)
    'pt': 'pt',   # Portuguese
    'por': 'pt',  # Portuguese (3-letter)
    'pl': 'pl',   # Polish
    'pol': 'pl',  # Polish (3-letter)
    'tr': 'tr',   # Turkish
    'tur': 'tr',  # Turkish (3-letter)
    'ru': 'ru',   # Russian
    'rus': 'ru',  # Russian (3-letter)
    'nl': 'nl',   # Dutch
    'nld': 'nl',  # Dutch (3-letter)
    'dut': 'nl',  # Dutch (3-letter alternative)
    'cs': 'cs',   # Czech
    'ces': 'cs',  # Czech (3-letter)
    'cze': 'cs',  # Czech (3-letter alternative)
    'ar': 'ar',   # Arabic
    'ara': 'ar',  # Arabic (3-letter)
    'zh': 'zh',   # Chinese
    'zho': 'zh',  # Chinese (3-letter)
    'chi': 'zh',  # Chinese (3-letter alternative)
    'ja': 'ja',   # Japanese
    'jpn': 'ja',  # Japanese (3-letter)
    'ko': 'ko',   # Korean
    'kor': 'ko',  # Korean (3-letter)
    'hi': 'hi',   # Hindi
    'hin': 'hi',  # Hindi (3-letter)
    'sv': 'sv',   # Swedish
    'swe': 'sv',  # Swedish (3-letter)
    'da': 'da',   # Danish
    'dan': 'da',  # Danish (3-letter)
    'no': 'no',   # Norwegian
    'nor': 'no',  # Norwegian (3-letter)
    'fi': 'fi',   # Finnish
    'fin': 'fi',  # Finnish (3-letter)
    'uk': 'uk',   # Ukrainian
    'ukr': 'uk',  # Ukrainian (3-letter)
    'el': 'el',   # Greek
    'ell': 'el',  # Greek (3-letter)
    'gre': 'el',  # Greek (3-letter alternative)
    'ro': 'ro',   # Romanian
    'ron': 'ro',  # Romanian (3-letter)
    'rum': 'ro',  # Romanian (3-letter alternative)
    'hu': 'hu',   # Hungarian
    'hun': 'hu',  # Hungarian (3-letter)
    'sr': 'sr',   # Serbian
    'srp': 'sr',  # Serbian (3-letter)
    'hr': 'hr',   # Croatian
    'hrv': 'hr',  # Croatian (3-letter)
    'bg': 'bg',   # Bulgarian
    'bul': 'bg',  # Bulgarian (3-letter)
    'sk': 'sk',   # Slovak
    'slk': 'sk',  # Slovak (3-letter)
    'slo': 'sk',  # Slovak (3-letter alternative)
    'sl': 'sl',   # Slovenian
    'slv': 'sl',  # Slovenian (3-letter)
    'lt': 'lt',   # Lithuanian
    'lit': 'lt',  # Lithuanian (3-letter)
    'lv': 'lv',   # Latvian
    'lav': 'lv',  # Latvian (3-letter)
    'et': 'et',   # Estonian
    'est': 'et',  # Estonian (3-letter)
    'ga': 'ga',   # Irish
    'gle': 'ga',  # Irish (3-letter)
    'vi': 'vi',   # Vietnamese
    'vie': 'vi',  # Vietnamese (3-letter)
    'th': 'th',   # Thai
    'tha': 'th',  # Thai (3-letter)
    'id': 'id',   # Indonesian
    'ind': 'id',  # Indonesian (3-letter)
    'ms': 'ms',   # Malay
    'msa': 'ms',  # Malay (3-letter)
    'may': 'ms',  # Malay (3-letter alternative)
    'he': 'he',   # Hebrew
    'heb': 'he',  # Hebrew (3-letter)
    'fa': 'fa',   # Persian
    'fas': 'fa',  # Persian (3-letter)
    'per': 'fa',  # Persian (3-letter alternative)
    'ca': 'ca',   # Catalan
    'cat': 'ca',  # Catalan (3-letter)
}


# -----------------------------
# Transliteration
# -----------------------------
def force_latin(text: str) -> str:
    """Convert Serbian Cyrillic to Latin while keeping Latin text unchanged."""
    try:
        return translit(text, "sr", reversed=True)
    except Exception:
        return text


# -----------------------------
# Hallucination / garbage filter
# -----------------------------
def is_hallucination(text: str, config: dict = None) -> bool:
    """Detect and remove hallucinated or filler text."""
    text_l = text.lower().strip()

    # Get filter settings from config or use defaults
    if config and "hallucination_filters" in config:
        filters = config["hallucination_filters"]
        bad_phrases = filters.get("bad_phrases", [])
        bad_patterns = filters.get("bad_patterns", [])
        min_word_length = filters.get("min_word_length", 8)
    else:
        # Default filters
        bad_phrases = [
            "hvala što pratite kanal",
            "Hvala vam.",
            "subscribe",
            "captioned by",
            "prodavanje",
            "teksting av",
            "thanks for watching",
            "teksting av nicolai winther",
        ]
        bad_patterns = [
            r"m{3,}", r"a{3,}", r"o{3,}", r"e{3,}", r"u{3,}", r"h{3,}",
            r"u+h+", r"m+h+",
            r'\b(\w{2,})\s+\1\s+\1',
            r'(\w+),\s*\1,\s*\1',
            r'(\w+\s+\w+),\s*\1,\s*\1',
            r"ok{3,}",
            r"ljo(\s+ljo){2,}",
        ]
        min_word_length = 8

    # Check bad phrases (exact match)
    if any(p.lower() in text_l for p in bad_phrases):
        return True

    # Check bad patterns (regex match)
    for pattern in bad_patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error:
            # If regex is invalid, fall back to string matching
            if pattern.lower() in text_l:
                return True

    # Check for very short text
    if len(text_l.split()) <= 1 and len(text_l) < min_word_length:
        return True

    return False


# -----------------------------
# System checks
# -----------------------------
def check_ffmpeg():
    """Check if FFmpeg is installed and available."""
    if not shutil.which("ffmpeg"):
        print("❌ Error: FFmpeg is not installed or not in PATH.")
        print("   Install FFmpeg:")
        print("   - Windows: winget install FFmpeg  or download from https://ffmpeg.org")
        print("   - Linux: sudo apt install ffmpeg")
        print("   - macOS: brew install ffmpeg")
        sys.exit(1)


def check_gpu_available(device: str):
    """Check if GPU/CUDA is available when requested."""
    if device == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                print("⚠️  Warning: CUDA requested but not available. Falling back to CPU.")
                print("   This will be significantly slower (10-50x).")
                return "cpu"
            else:
                print(f"✅  GPU detected: {torch.cuda.get_device_name(0)}")
                return "cuda"
        except ImportError:
            print("⚠️  Warning: PyTorch not installed. Falling back to CPU.")
            print("   Install with: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
            return "cpu"
    return device


def load_config(config_path: str = "config.yaml"):
    """Load configuration from YAML file if it exists."""
    if yaml is None:
        return {}

    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            print(f"📝 Loaded configuration from {config_path}")
            return config or {}
    except Exception as e:
        print(f"⚠️  Warning: Failed to load config file: {e}")
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
    logging.info("Transcription session started")


# -----------------------------
# FFmpeg-based preprocessing
# -----------------------------
def preprocess_audio(input_path: str, progress_callback=None, job_id=None, active_processes_dict=None) -> str:
    """
    Extract and denoise audio using FFmpeg with RNNoise + Loudnorm (if available).
    Returns path to temporary clean WAV.

    Args:
        input_path: Path to input video/audio file
        progress_callback: Optional callback for progress updates
        job_id: Optional job ID for process tracking
        active_processes_dict: Optional dict to store active process for cancellation
    """
    base, _ = os.path.splitext(input_path)
    clean_audio = base + "_clean.wav"

    if os.path.exists(clean_audio) and os.path.getsize(clean_audio) > 4096:
        return clean_audio

    print(f"🎧 Preprocessing audio for {os.path.basename(input_path)} ...")
    logging.info(f"Starting audio preprocessing for {input_path}")

    # Get video duration for progress calculation
    duration = None
    try:
        import json
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "json", input_path]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(result.stdout)
        duration = float(probe_data.get('format', {}).get('duration', 0))
        logging.info(f"Video duration: {duration:.2f}s")
    except Exception as e:
        logging.warning(f"Could not get video duration: {e}")

    # Check if RNNoise model exists
    rnnoise_path = os.path.join("rnnoise-models", "rnnoise-model.bin")
    if os.path.exists(rnnoise_path):
        ffmpeg_filters = f"arnndn=m={rnnoise_path},loudnorm,highpass=f=200"
    else:
        print("   ⚠️ RNNoise model not found, using loudnorm + highpass only.")
        ffmpeg_filters = "loudnorm,highpass=f=200"

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "info", "-progress", "pipe:1",
        "-i", input_path,
        "-ac", "1", "-ar", "16000",
        "-af", ffmpeg_filters,
        clean_audio
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )

        # Register process for cancellation if job_id provided
        if job_id and active_processes_dict is not None:
            active_processes_dict[job_id] = process
            logging.info(f"Registered ffmpeg process {process.pid} for job {job_id}")

        # Parse ffmpeg progress output
        import re
        time_pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')

        for line in process.stdout:
            if 'time=' in line:
                match = time_pattern.search(line)
                if match and duration:
                    hours, minutes, seconds = match.groups()
                    current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    progress_percent = min((current_time / duration) * 100, 100)

                    # Map to 1-3% range for audio extraction
                    final_progress = 1 + int(progress_percent * 2 / 100)  # 1% to 3%

                    if progress_callback:
                        duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}"
                        progress_callback(final_progress, f"Extracting audio... ({int(progress_percent)}%) {duration_str}")

                    logging.debug(f"FFmpeg progress: {current_time:.1f}s / {duration:.1f}s ({progress_percent:.1f}%)")

        process.wait()

        # Clean up process registration
        if job_id and active_processes_dict is not None:
            active_processes_dict.pop(job_id, None)
            logging.info(f"Unregistered ffmpeg process for job {job_id}")

        if process.returncode == 0:
            if os.path.exists(clean_audio) and os.path.getsize(clean_audio) > 4096:
                print("   ✅ Audio cleaned and normalized.")
                logging.info(f"Audio preprocessing completed: {clean_audio}")
                return clean_audio
            else:
                print("   ⚠️ Audio file too small or empty after filtering, using raw input.")
                logging.warning("Audio file too small after preprocessing")
                return input_path
        else:
            stderr_output = process.stderr.read()
            logging.error(f"FFmpeg failed with code {process.returncode}: {stderr_output}")
            print(f"   ⚠️ FFmpeg preprocessing failed, using raw input.")
            return input_path

    except Exception as e:
        # Clean up process registration on error
        if job_id and active_processes_dict is not None:
            active_processes_dict.pop(job_id, None)

        print(f"   ⚠️ FFmpeg preprocessing failed ({e}), using raw input.")
        logging.error(f"Audio preprocessing exception: {e}", exc_info=True)
        return input_path

# -----------------------------
# Core transcription function (importable)
# -----------------------------
def transcribe_file(
    input_path,
    output_path=None,
    model_name="large-v3",
    device="cuda",
    compute_type="float16",
    language="sr",
    beam_size=12,
    vad_filter=False,
    temperature=0.2,
    no_speech_threshold=0.1,
    compression_threshold=2.8,
    chunk_length=None,
    progress_callback=None,
    config=None,
    job_id=None,
    active_processes_dict=None
):
    """
    Transcribe audio/video file to SRT subtitles.

    Args:
        input_path: Path to input media file
        output_path: Path to output SRT file (auto-generated if None)
        model_name: Whisper model name (tiny, small, medium, large-v3)
        device: 'cuda' or 'cpu'
        compute_type: 'float16', 'float32', or 'int8_float16'
        language: Language code (e.g., 'sr', 'en', 'ru')
        beam_size: Beam search size (higher = more accurate, slower)
        vad_filter: Enable voice activity detection
        temperature: Temperature for sampling (0.0 = deterministic)
        no_speech_threshold: Threshold for no-speech segments
        compression_threshold: Compression ratio threshold
        chunk_length: Audio chunk length in seconds (None = auto)
        progress_callback: Optional callback function(progress_pct, message)
        config: Optional config dict (overrides default config.yaml)

    Returns:
        tuple: (output_path, segment_count) on success

    Raises:
        FileNotFoundError: If input file doesn't exist
        RuntimeError: If transcription fails
    """

    # Load config if not provided
    if config is None:
        config = load_config()

    # Validate input
    input_path = os.path.abspath(input_path)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Generate output path if not provided
    if output_path is None:
        base, _ = os.path.splitext(input_path)
        lang_suffix = LANGUAGE_SUFFIX_MAP.get(language, language)
        output_path = f"{base}.{lang_suffix}.srt"

    # Check if output already exists
    if os.path.exists(output_path):
        if progress_callback:
            progress_callback(100, f"Subtitle already exists: {output_path}")
        logging.info(f"Skipped (subtitle exists): {input_path}")
        return output_path, 0

    logging.info(f"Starting transcription: {input_path}")
    logging.info(f"Model: {model_name}, Device: {device}, Beam: {beam_size}")

    if progress_callback:
        progress_callback(1, "Analyzing video...")

    # Audio preprocessing with progress tracking (1% -> 3%)
    audio_source = preprocess_audio(
        input_path,
        progress_callback=progress_callback,
        job_id=job_id,
        active_processes_dict=active_processes_dict
    )

    if progress_callback:
        progress_callback(4, f"Loading model '{model_name}'...")

    # Load model
    try:
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
    except Exception as e:
        error_msg = f"Error loading model: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    if progress_callback:
        progress_callback(5, "Starting transcription...")

    # Transcription
    try:
        segments, info = model.transcribe(
            audio_source,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            temperature=temperature,
            compression_ratio_threshold=compression_threshold,
            no_speech_threshold=no_speech_threshold,
            condition_on_previous_text=False,
            chunk_length=chunk_length,
            max_initial_timestamp=0.0,
        )

        detected_lang = info.language
        logging.info(f"Detected language: {detected_lang} ({info.language_probability:.2f})")

        if progress_callback:
            progress_callback(8, f"Language detected: {detected_lang} - Processing segments...")

    except Exception as e:
        error_msg = f"Error during transcription: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    if progress_callback:
        progress_callback(10, "Processing and writing segments...")

    # Write SRT subtitles
    hallucination_config = config.get("hallucination_filters", {})
    min_duration = hallucination_config.get("min_segment_duration", 0.3)

    try:
        segment_count = 0
        total_segments_processed = 0
        last_progress_update = 0
        current_timestamp = 0

        # Collect all segments first to avoid keeping iterator open
        all_segments = list(segments)

        with open(output_path, "w", encoding="utf-8") as srt:
            for seg in all_segments:
                total_segments_processed += 1
                current_timestamp = seg.end

                text = force_latin(seg.text.strip())
                if (seg.end - seg.start) < min_duration or is_hallucination(text, config):
                    continue

                segment_count += 1
                srt.write(f"{segment_count}\n")
                srt.write(
                    f"{int(seg.start // 3600):02d}:{int((seg.start % 3600)//60):02d}:{int(seg.start%60):02d},{int((seg.start*1000)%1000):03d} --> "
                    f"{int(seg.end // 3600):02d}:{int((seg.end % 3600)//60):02d}:{int(seg.end%60):02d},{int((seg.end*1000)%1000):03d}\n"
                )
                srt.write(f"{text}\n\n")

                # Update progress every 10 segments (10% to 90% range)
                if progress_callback and total_segments_processed % 10 == 0:
                    # Calculate progress based on time (assuming typical video length)
                    progress = min(10 + int((current_timestamp / 60) * 5), 90)  # Roughly 5% per minute, capped at 90%
                    if progress > last_progress_update:
                        time_str = f"{int(current_timestamp // 60)}:{int(current_timestamp % 60):02d}"
                        progress_callback(progress, f"Writing segment {segment_count} at {time_str}...")
                        last_progress_update = progress
                        logging.info(f"Progress: {segment_count} segments written (at {time_str})")

        # Explicitly flush and close to release file handle
        logging.info(f"Transcription completed: {output_path} ({segment_count} segments)")

        if progress_callback:
            progress_callback(95, f"Finalizing... Saved {segment_count} segments")

    except IOError as e:
        error_msg = f"Error writing subtitle file: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    # Cleanup temporary audio
    if audio_source != input_path and os.path.exists(audio_source):
        try:
            os.remove(audio_source)
        except Exception:
            pass

    # Force garbage collection to release any file handles
    import gc
    gc.collect()

    if progress_callback:
        progress_callback(100, f"Completed: {segment_count} segments")

    return output_path, segment_count


# -----------------------------
# Main CLI routine
# -----------------------------
def main():
    # Load configuration file
    config = load_config()
    trans_config = config.get("transcription", {})

    # Setup logging
    setup_logging(config)

    parser = argparse.ArgumentParser(description="Transcribe video/audio to Latin .srt using faster-whisper (CUDA).")
    parser.add_argument("input_file", help="Path to media file (.mp4, .wav, etc.)")
    parser.add_argument("--model", default=trans_config.get("model", "large-v3"),
                       help="Model name (tiny, small, medium, large-v2, large-v3)")
    parser.add_argument("--device", default=trans_config.get("device", "cuda"),
                       help="Device: cuda or cpu")
    parser.add_argument("--compute", default=trans_config.get("compute", "float16"),
                       help="Compute precision (float16, float32, int8_float16)")
    parser.add_argument("--language", default=trans_config.get("language", "sr"),
                       help="Language code, e.g. sr, en, ru")
    parser.add_argument("--beam", type=int, default=trans_config.get("beam_size", 12),
                       help="Beam size (higher improves accuracy)")
    parser.add_argument("--vad", type=lambda x: str(x).lower() in ("true", "1", "yes"),
                       default=trans_config.get("vad_filter", False), help="Enable VAD")
    parser.add_argument("--temp", type=float, default=trans_config.get("temperature", 0.2),
                       help="Temperature (0.0 deterministic, 0.2–0.4 noisy speech)")
    parser.add_argument("--no-speech-threshold", type=float,
                       default=trans_config.get("no_speech_threshold", 0.1),
                       help="No-speech probability threshold")
    parser.add_argument("--compression-threshold", type=float,
                       default=trans_config.get("compression_threshold", 2.8),
                       help="Compression ratio threshold")
    parser.add_argument("--chunk-length", type=float, default=None,
                       help="Chunk length in seconds (None=auto)")
    args = parser.parse_args()

    # System checks
    check_ffmpeg()
    args.device = check_gpu_available(args.device)

    # Progress callback for CLI
    def cli_progress(percent, message):
        if percent <= 10:
            print(f"🔹 {message}")
        elif percent >= 95:
            print(f"✅ {message}")

    # Call core transcription function
    try:
        output_path, segment_count = transcribe_file(
            input_path=args.input_file,
            model_name=args.model,
            device=args.device,
            compute_type=args.compute,
            language=args.language,
            beam_size=args.beam,
            vad_filter=args.vad,
            temperature=args.temp,
            no_speech_threshold=args.no_speech_threshold,
            compression_threshold=args.compression_threshold,
            chunk_length=args.chunk_length,
            progress_callback=cli_progress,
            config=config
        )

        print(f"✅ Subtitles saved: {output_path} ({segment_count} segments)")

    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ {e}")
        if "out of memory" in str(e).lower():
            print("   GPU out of memory. Try:")
            print("   - Smaller model: --model medium or --model small")
            print("   - CPU mode: --device cpu")
        elif "model" in str(e).lower():
            print(f"   Available models: tiny, small, medium, large-v2, large-v3")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
