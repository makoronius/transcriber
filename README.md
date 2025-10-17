# Whisper AI Transcriber

**GPU-accelerated YouTube transcription with automatic subtitle generation**

A powerful web-based transcription system that downloads YouTube videos and generates accurate subtitles using OpenAI's Whisper model with CUDA acceleration. Features a modern web interface, real-time progress tracking, and advanced hallucination filtering optimized for Serbian content with Cyrillic-to-Latin transliteration.

---

## ✨ Features

### 🌐 Modern Web Interface
- **Real-time monitoring** with WebSocket updates
- **Background job processing** - continues even when browser is closed
- **File browser** with video player and subtitle editor
- **System monitoring** dashboard with auto-refresh
- **Upload support** for local video files
- **Translation features** for subtitles

### 🚀 Performance
- **GPU acceleration** with CUDA support (10-50x faster than CPU)
- **Parallel processing** - multiple videos transcribed simultaneously
- **Smart resume** - automatically detects existing downloads
- **Live queue** - transcription starts immediately as downloads complete

### 🎯 Quality
- **Advanced hallucination filtering** - removes filler words and repeated patterns
- **Cyrillic transliteration** - automatic Serbian Cyrillic to Latin conversion
- **VAD (Voice Activity Detection)** - improves accuracy by removing non-speech
- **Configurable models** - from tiny (fast) to large-v3 (highest quality)

### 🔧 Flexibility
- **Multiple installation methods** - Docker, WSL, native Windows, Ubuntu/Linux
- **Cookie support** - download age-restricted and private videos
- **Audio enhancement** - FFmpeg preprocessing with noise reduction
- **Multi-language** - supports 90+ languages with auto-detection

---

## 🎬 Demo

### Web Interface
- Submit YouTube URLs or upload video files
- Monitor transcription progress in real-time
- Browse, search, and download generated subtitles
- Play videos with synchronized subtitles

### Command Line
Traditional CLI tools available for batch processing and automation.

---

## 📚 Documentation

### Quick Start
- **[Installation Guide](docs/INSTALLATION.md)** - Native, WSL, Docker installations
- **[Docker Setup](docs/DOCKER_SETUP.md)** - Containerized deployment
- **[Web Interface Guide](docs/WEB_INTERFACE.md)** - Web UI documentation
- **[Usage Guide](docs/USAGE.md)** - CLI and advanced usage

### Requirements
- **Python 3.8-3.12** (3.12 recommended for GPU support)
- **FFmpeg** for audio processing
- **CUDA-capable GPU** (optional but highly recommended)
- **10+ GB disk space** for models and videos

See [Installation Guide](docs/INSTALLATION.md) for detailed requirements and setup instructions.

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
docker-compose up -d
# Access at http://localhost:5001
```

### Option 2: Native Installation
```bash
pip install -r requirements.txt
python web_app.py
# Access at http://localhost:5000
```

See [Installation Guide](docs/INSTALLATION.md) for detailed instructions for your platform.

---

## 🎯 Use Cases

- **Content Creation** - Generate subtitles for YouTube videos
- **Education** - Transcribe lectures and educational content
- **Accessibility** - Create subtitles for hearing-impaired viewers
- **Research** - Analyze video content through text transcription
- **Localization** - Translate subtitles to multiple languages
- **Archive** - Preserve video content with searchable text

---

## 🏗️ Architecture

### Components
- **Web Application** - Flask-based REST API with WebSocket support
- **Transcription Engine** - faster-whisper with CUDA acceleration
- **Download Manager** - yt-dlp for YouTube video acquisition
- **Audio Processor** - FFmpeg with noise reduction pipeline
- **Database** - SQLite for job tracking and metadata
- **File Browser** - React-style interface for file management

### Technology Stack
- **Backend**: Python, Flask, SocketIO
- **Transcription**: faster-whisper, PyTorch, CUDA
- **Frontend**: Vanilla JavaScript, CSS3
- **Containerization**: Docker, Docker Compose
- **Video Processing**: FFmpeg, yt-dlp

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests, report bugs, or suggest features.

### Development Setup
```bash
git clone https://github.com/makoronius/transcriber.git
cd transcriber
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📧 Contact

**Mark Emelianov**
Email: [mark.emelianov@gmail.com](mailto:mark.emelianov@gmail.com)
GitHub: [makoronius](https://github.com/makoronius)

For bug reports and feature requests, please use [GitHub Issues](https://github.com/makoronius/transcriber/issues).

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

This project builds upon excellent open-source tools:

- **[faster-whisper](https://github.com/guillaumekln/faster-whisper)** by Guillaume Klein - Optimized Whisper implementation
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - YouTube video downloader
- **[OpenAI Whisper](https://github.com/openai/whisper)** - Speech recognition model
- **[PyTorch](https://pytorch.org/)** - Deep learning framework
- **[FFmpeg](https://ffmpeg.org/)** - Multimedia processing
- **[Flask](https://flask.palletsprojects.com/)** - Web framework
- **[Socket.IO](https://socket.io/)** - Real-time communication

---

## ⚖️ Legal Notice

**Important**: This tool is for personal and educational use only.

- Respect YouTube's [Terms of Service](https://www.youtube.com/t/terms)
- Only download content you have permission to access
- Respect copyright laws and content creators' rights
- Do not use for commercial purposes without proper licensing
- Age-restricted content requires authentication via cookies

The authors are not responsible for misuse of this software.

---

## 📊 Project Stats

- **Languages**: Python, JavaScript, CSS
- **Code**: 16,000+ lines
- **Models**: 5 Whisper models supported (tiny to large-v3)
- **Platforms**: Windows, Linux, macOS, WSL, Docker
- **Languages Supported**: 90+ via Whisper

---

## 🗺️ Roadmap

- [ ] Multi-user support with authentication
- [ ] Cloud storage integration (S3, Google Drive)
- [ ] Advanced subtitle editing features
- [ ] Real-time transcription for live streams
- [ ] Mobile-responsive web interface
- [ ] API documentation with Swagger/OpenAPI
- [ ] Docker Hub images for easier deployment
- [ ] Batch translation with multiple LLM providers

---

**Made with ❤️ by Mark Emelianov**
# CI/CD Pipeline Active
# Webhook Test 2
# Test 3
# Test 4
# Test 5 - Final
# Final deployment test
# FINAL TEST - Docker Fixed
# Success!
# CI/CD WORKING - AUTOMATIC DEPLOYMENT ENABLED!
# Testing automatic deployment - Thu, Oct 16, 2025  8:20:14 PM
# Final test of automatic deployment - Thu, Oct 16, 2025  8:22:29 PM
# Testing deployment verification - Oct 17, 2025
